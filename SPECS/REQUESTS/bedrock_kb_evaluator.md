# Bedrock Knowledge Base Evaluator

Add Amazon Bedrock Knowledge Bases as evaluation mode alongside existing modes (hybrid, dense, openai, kendra, vertex).

## Context

- Knowledge Base ID: `371M2G58TV`
- Vector Store: OpenSearch Serverless
- Embedding Model: Titan Text Embeddings V2
- Chunking: Default (~300 tokens)

## Implementation Steps

### 1. Create `evaluation/bedrock_evaluator.py`

```python
"""Bedrock Knowledge Base evaluator"""
import os
import time
import boto3

class BedrockKBEvaluator:
    """Evaluator that uses Amazon Bedrock Knowledge Bases"""

    def __init__(self):
        self.kb_id = os.getenv('BEDROCK_KB_ID', '371M2G58TV')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.client = boto3.client('bedrock-agent-runtime', region_name=self.region)
        # Model for generation (Claude or Titan)
        self.model_arn = f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"

    def query(self, question: str, debug: bool = False) -> dict:
        """Query Bedrock KB and return response with timing"""
        start_time = time.time()

        response = self.client.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': self.model_arn
                }
            }
        )

        response_time = time.time() - start_time

        # Extract answer
        answer = response['output']['text']

        # Extract sources/citations
        sources = []
        if 'citations' in response:
            for citation in response['citations']:
                for ref in citation.get('retrievedReferences', []):
                    location = ref.get('location', {})
                    s3_uri = location.get('s3Location', {}).get('uri', '')
                    # Extract filename from S3 URI
                    doc_name = s3_uri.split('/')[-1] if s3_uri else 'unknown'
                    sources.append({
                        'doc': doc_name,
                        'page': 'N/A',  # Bedrock doesn't track page numbers
                        'score': ref.get('score', 0)
                    })

        result = {
            'answer': answer,
            'sources': sources,
            'response_type': 'bedrock_kb',
            'response_time': response_time
        }

        if debug:
            result['debug_info'] = {
                'kb_id': self.kb_id,
                'model_arn': self.model_arn,
                'raw_response': response
            }

        return result
```

### 2. Update `evaluation/config.py`

Add 'bedrock' to VALID_MODES:

```python
VALID_MODES = ['hybrid', 'dense', 'openai', 'kendra', 'vertex', 'bedrock']
```

### 3. Update `evaluation/run_evaluation.py`

Add bedrock case in the evaluator selection block (~line 93):

```python
elif mode == 'bedrock':
    try:
        from .bedrock_evaluator import BedrockKBEvaluator
    except ImportError:
        from evaluation.bedrock_evaluator import BedrockKBEvaluator
    custom_evaluator = BedrockKBEvaluator()
    print("Evaluator: Amazon Bedrock Knowledge Base (Titan Embeddings + Claude Haiku)")
```

### 4. Environment Variable

Ensure env var is set (optional, defaults to hardcoded ID):

```bash
export BEDROCK_KB_ID="371M2G58TV"
```

## Usage

```bash
# Run Bedrock KB evaluation
python -m evaluation.run_evaluation --mode bedrock

# Test with limit
python -m evaluation.run_evaluation --mode bedrock --test --limit 5

# Debug mode
python -m evaluation.run_evaluation --mode bedrock --debug --limit 3
```

## Output

Results will be saved to: `results/bedrock/RUN_<timestamp>/`

## Notes

1. **No page numbers** - Bedrock KB doesn't preserve PDF page metadata, so sources will show `page: N/A`
2. **Model choice** - Using Claude Haiku for generation (fast, cheap). Can switch to Claude Sonnet for better quality.
3. **boto3 dependency** - Already installed (used by Kendra evaluator)
4. **AWS credentials** - Same credentials used for Kendra should work

## Comparison Value

This evaluator will show how your custom pipeline (3-tier contextual embeddings + hybrid search + adaptive reranking) compares against AWS's managed "upload and go" solution with:
- Default chunking (~300 tokens)
- Titan embeddings (dense only)
- No custom reranking
- No contextual enrichment

## Files to Modify

| File | Change |
|------|--------|
| `evaluation/bedrock_evaluator.py` | Create new file |
| `evaluation/config.py` | Add 'bedrock' to VALID_MODES |
| `evaluation/run_evaluation.py` | Add bedrock evaluator case |
