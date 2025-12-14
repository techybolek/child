# Bedrock Knowledge Base Evaluator

Evaluates the RAG chatbot against Amazon Bedrock Knowledge Bases - AWS's managed RAG solution.

## Quick Start

```bash
# Run evaluation
python -m evaluation.run_evaluation --mode bedrock

# With specific model
BEDROCK_MODEL=nova-pro python -m evaluation.run_evaluation --mode bedrock

# Test mode
python -m evaluation.run_evaluation --mode bedrock --test --limit 5
```

## Architecture

```
Question
    ↓
BedrockKBEvaluator
    ↓
Bedrock Agent Runtime (retrieve_and_generate)
    ↓
Knowledge Base (371M2G58TV)
    ├── OpenSearch Serverless (vector store)
    ├── Titan Text Embeddings V2 (embeddings)
    └── Amazon Nova Micro (generation)
    ↓
Answer + Citations
    ↓
LLM Judge (scoring)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_KB_ID` | `371M2G58TV` | Knowledge Base ID |
| `BEDROCK_MODEL` | `nova-micro` | Generation model |
| `AWS_REGION` | `us-east-1` | AWS region |

### Available Models

**Amazon (no approval required):**
- `nova-micro` - Fast, default
- `nova-lite` - Balanced
- `nova-pro` - High quality

**Anthropic (requires use case form):**
- `3-haiku` - Claude 3 Haiku
- `3.5-haiku` - Claude 3.5 Haiku
- `4-5` - Claude Haiku 4.5

## Knowledge Base Setup

**S3 Bucket:** `cohort-tx-1` (24 PDFs)

**Sync documents:**
```python
import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
client.start_ingestion_job(
    knowledgeBaseId='371M2G58TV',
    dataSourceId='V4C2EUGYSY'
)
```

## Key Files

| File | Purpose |
|------|---------|
| `evaluation/bedrock_evaluator.py` | Main evaluator class |
| `evaluation/bedrock_model_resolver.py` | Model name resolution |
| `tests/test_evaluation_e2e_bedrock.py` | E2E tests |
| `scripts/validate_bedrock_evaluator.sh` | Validation script |

## Limitations

1. **No page numbers** - Bedrock KB doesn't preserve PDF page metadata
2. **Default chunking** - ~300 tokens (vs custom 1000 chars)
3. **Dense only** - No hybrid search (vs custom RRF fusion)
4. **No reranking** - No adaptive chunk selection

## Comparison Value

Tests managed AWS RAG against custom pipeline:

| Feature | Bedrock KB | Custom Pipeline |
|---------|------------|-----------------|
| Embeddings | Titan V2 (dense) | OpenAI + BM25 (hybrid) |
| Chunking | ~300 tokens | 1000 chars + context |
| Reranking | None | LLM adaptive |
| Context | None | 3-tier contextual |

## Validation

```bash
./scripts/validate_bedrock_evaluator.sh
```

Runs:
1. CLI help verification
2. Quick evaluation (limit 3)
3. Debug mode test
4. E2E pytest suite
5. Regression tests (hybrid, kendra)
