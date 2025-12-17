# Issue: Bedrock KB Returns No Citations With Custom Prompt

## Status
**Resolved** - Fixed on 2025-12-17.

### Resolution
- Added `$output_format_instructions$` placeholder to prompt template in `bedrock_kb_handler.py`
- Added regression test `test_citations_returned_with_custom_prompt` in `tests/test_bedrock_kb_handler.py`
- All tests pass (16/16 handler tests, 5/5 integration tests)

## Problem Description

After implementing the citation hallucination fix (which correctly extracts citations from the API response instead of parsing LLM text), the `BedrockKBHandler` returns **no citations at all**.

**Observed Behavior:**
- Handler response contains `sources: []` (empty list)
- API `response['citations']` contains 1 citation with 0 `retrievedReferences`

**Expected Behavior:**
- Handler should return actual S3 filenames like `3202600043-eccs-rfp-twc.pdf`
- API should populate `retrievedReferences` with source documents

## Root Cause

The custom prompt template in `BedrockKBHandler._query_bedrock()` is missing the **`$output_format_instructions$`** placeholder variable that Bedrock requires for citations to work.

**Current template (broken):**
```python
'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
```

**Required template (working):**
```python
'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
```

The `$output_format_instructions$` placeholder contains Bedrock's internal instructions that tell the model how to format citations. Without it, Bedrock doesn't populate the `retrievedReferences` array.

## Evidence

### Test Results

| Configuration | Citations | retrievedReferences |
|---------------|-----------|---------------------|
| No custom prompt | 7 | 8 |
| Custom prompt WITHOUT `$output_format_instructions$` | 1 | 0 |
| Custom prompt WITH `$output_format_instructions$` | 3 | 11 |

### Validation Command

```bash
# Test WITHOUT $output_format_instructions$ (current - broken)
python -c "
import boto3
from chatbot import config
from chatbot.prompts import BEDROCK_AGENT_PROMPT

client = boto3.client('bedrock-agent-runtime', region_name=config.AWS_REGION)
response = client.retrieve_and_generate(
    input={'text': 'What is TWC?'},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': config.BEDROCK_KB_ID,
            'modelArn': f'arn:aws:bedrock:{config.AWS_REGION}::foundation-model/amazon.nova-micro-v1:0',
            'generationConfiguration': {
                'promptTemplate': {
                    'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\nQuestion: \$query\$\n\nSearch results:\n\$search_results\$'
                }
            }
        }
    }
)
citations = response.get('citations', [])
refs = sum(len(c.get('retrievedReferences', [])) for c in citations)
print(f'Citations: {len(citations)}, retrievedReferences: {refs}')
# Output: Citations: 1, retrievedReferences: 0
"

# Test WITH $output_format_instructions$ (fix - working)
python -c "
import boto3
from chatbot import config
from chatbot.prompts import BEDROCK_AGENT_PROMPT

client = boto3.client('bedrock-agent-runtime', region_name=config.AWS_REGION)
response = client.retrieve_and_generate(
    input={'text': 'What is TWC?'},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': config.BEDROCK_KB_ID,
            'modelArn': f'arn:aws:bedrock:{config.AWS_REGION}::foundation-model/amazon.nova-micro-v1:0',
            'generationConfiguration': {
                'promptTemplate': {
                    'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n\$output_format_instructions\$\n\nQuestion: \$query\$\n\nSearch results:\n\$search_results\$'
                }
            }
        }
    }
)
citations = response.get('citations', [])
refs = sum(len(c.get('retrievedReferences', [])) for c in citations)
print(f'Citations: {len(citations)}, retrievedReferences: {refs}')
# Output: Citations: 3, retrievedReferences: 11
"
```

## Solution

Add `$output_format_instructions$` placeholder to the custom prompt template in:

1. **`chatbot/handlers/bedrock_kb_handler.py`** (line ~130)
2. **`evaluation/bedrock_evaluator.py`** (for consistency - currently has no custom prompt)

### Code Change

```python
# In _query_bedrock() method
'generationConfiguration': {
    'promptTemplate': {
        'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
    }
}
```

## Files Affected

| File | Current State | Required Change |
|------|--------------|-----------------|
| `chatbot/handlers/bedrock_kb_handler.py` | Has custom prompt, missing `$output_format_instructions$` | Add placeholder |
| `evaluation/bedrock_evaluator.py` | No custom prompt | Add custom prompt with placeholder (optional, for consistency) |

## Reference

- AWS re:Post: [RetrieveAndGenerate API response is giving empty list for retrievedReferences](https://repost.aws/questions/QUEyzghKt6RzCWqyBpifaTUg)
- AWS Bedrock Documentation: Custom prompts require `$output_format_instructions$` for citation functionality

## Related Issues

- Citation hallucination fix (implemented) - Changed citation extraction from LLM text parsing to API response parsing
