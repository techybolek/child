# Bedrock KB Citation Hallucination Issue

**Status:** Identified
**Severity:** Medium
**Date:** 2025-12-17

## Problem

The Bedrock KB handler returns fabricated/hallucinated citations that don't exist in the knowledge base.

**Examples of bogus citations:**
- `WD Letter 24-23, Attachment 1.pdf`
- `23 I Page FFY 2025-2027 CCDF State Plan.pdf`
- `4.pdf`

**Actual KB filenames:**
- `wd-24-23-att1-twc.pdf`
- `tx-ccdf-state-plan-ffy2025-2027-approved.pdf`

## Root Cause

The `BedrockKBHandler` and `BedrockKBEvaluator` use different citation extraction methods:

| Component | Citation Source | Result |
|-----------|----------------|--------|
| `BedrockKBHandler` | Parses LLM text output | **Hallucinated** filenames |
| `BedrockKBEvaluator` | API `response['citations']` | **Correct** S3 URIs |

### Why the Handler Gets Wrong Citations

1. The handler uses a custom prompt template (`chatbot/prompts/bedrock_agent_prompt.py`)
2. The prompt instructs the LLM to output `SOURCES:\n- [filename.pdf]`
3. The `$search_results$` placeholder only contains **text content**, not filename metadata
4. The LLM invents human-readable document titles based on content it reads
5. The handler parses these invented names from the LLM's text output

### Code Analysis

**Handler (WRONG approach)** - `chatbot/handlers/bedrock_kb_handler.py:54-89`:
```python
def _parse_response(self, output_text: str):
    # Parses LLM-generated text - filenames are hallucinated
    sources_match = re.search(r'SOURCES:\s*\n(.*?)$', output_text, re.DOTALL)
    for line in sources_text.split('\n'):
        if line.startswith('- '):
            doc_name = line[2:].strip()  # LLM made this up
```

**Evaluator (CORRECT approach)** - `evaluation/bedrock_evaluator.py:68-85`:
```python
# Parses API response - filenames are real S3 URIs
citations = response.get('citations', [])
for citation in citations:
    for ref in citation.get('retrievedReferences', []):
        uri = ref.get('location', {}).get('s3Location', {}).get('uri', '')
        doc_name = uri.split('/')[-1]  # Actual filename
```

## Solution

Modify `BedrockKBHandler` to extract citations from the API response instead of parsing LLM text output.

### Implementation Steps

1. **Modify `_query_bedrock()`** to return raw API response (or extract citations)
2. **Add `_extract_citations()`** method similar to evaluator
3. **Update `_parse_response()`** to only extract ANSWER section
4. **Update `handle()`/`handle_async()`** to use API-sourced citations
5. **Optionally** remove SOURCES section from prompt (no longer needed)

### Files to Modify

- `chatbot/handlers/bedrock_kb_handler.py` - Main fix
- `chatbot/prompts/bedrock_agent_prompt.py` - Remove SOURCES instructions (optional)
- `tests/test_bedrock_kb_handler.py` - Update tests

## Verification

After fix:
1. Run query with `debug=True`
2. Verify returned `sources[*].doc` matches actual KB filenames
3. Filenames should follow pattern: `lowercase-with-dashes-twc.pdf`

## Notes

- The evaluator works correctly because it never relied on LLM-generated citations
- The prompt's `$search_results$` placeholder from Bedrock does NOT expose filename metadata to the LLM
- This is a fundamental limitation of Bedrock's prompt template system
