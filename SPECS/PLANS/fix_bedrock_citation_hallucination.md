# Bug: Bedrock KB Citation Hallucination

## Bug Description
The `BedrockKBHandler` returns fabricated/hallucinated citations that don't exist in the knowledge base. For example, it returns citations like `WD Letter 24-23, Attachment 1.pdf` and `23 I Page FFY 2025-2027 CCDF State Plan.pdf` when the actual KB filenames are `wd-24-23-att1-twc.pdf` and `tx-ccdf-state-plan-ffy2025-2027-approved.pdf`.

**Expected behavior:** Citations should be actual filenames from the Bedrock Knowledge Base S3 bucket (e.g., `wd-24-23-att1-twc.pdf`)

**Actual behavior:** Citations are human-readable document titles invented by the LLM based on document content (e.g., `WD Letter 24-23, Attachment 1.pdf`)

## Problem Statement
The handler uses a prompt template that instructs the LLM to output `SOURCES:\n- [filename.pdf]`, but the `$search_results$` placeholder in Bedrock's API only contains text content, not filename metadata. The LLM has no access to actual filenames, so it invents human-readable titles based on document content. The handler then parses these invented names from the LLM's text output.

## Solution Statement
Modify `BedrockKBHandler` to extract citations from the Bedrock API response (`response['citations']`) instead of parsing LLM-generated text output. This mirrors the correct approach already used by `BedrockKBEvaluator`. The prompt's SOURCES instructions should also be removed since they're no longer needed and cause confusion.

## Steps to Reproduce
1. Run the handler with a query:
   ```python
   from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
   handler = BedrockKBHandler()
   response = handler.handle("What is the income limit for a family of 4?", debug=True)
   print(response['sources'])
   print(response['debug_info']['raw_output'])
   ```
2. Observe that `sources[*].doc` contains invented filenames like `WD Letter 24-23, Attachment 1.pdf`
3. Compare against actual KB filenames which follow pattern: `lowercase-with-dashes-twc.pdf`

## Root Cause Analysis
The `_query_bedrock()` method returns only `output_text` from the Bedrock API response, discarding the `citations` array which contains actual S3 URIs. The `_parse_response()` method then parses the LLM's text output looking for `SOURCES:` section, extracting whatever filenames the LLM invented.

**Handler flow (WRONG):**
```
API Response → extract output.text → parse SOURCES section → hallucinated filenames
```

**Evaluator flow (CORRECT):**
```
API Response → extract citations[].retrievedReferences[].location.s3Location.uri → real filenames
```

The LLM cannot provide accurate citations because:
1. The `$search_results$` placeholder only exposes text content, not metadata
2. Bedrock doesn't expose source filenames to the generation model
3. The LLM compensates by generating human-readable document titles from content

## Relevant Files
Use these files to fix the bug:

- `chatbot/handlers/bedrock_kb_handler.py` - Main fix location. The `_query_bedrock()` method must return the full API response (or at least citations), and a new `_extract_citations()` method should parse S3 URIs from the citations array. The `_parse_response()` method should only extract the ANSWER section.
- `chatbot/prompts/bedrock_agent_prompt.py` - Remove the SOURCES output format instructions since citations now come from the API response, not LLM text.
- `tests/test_bedrock_kb_handler.py` - Update tests to verify that returned sources have actual KB filenames (lowercase with dashes), not invented titles.
- `evaluation/bedrock_evaluator.py` - Reference implementation showing correct citation extraction (lines 68-85). Use this as the model for the fix.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Update `_query_bedrock()` to Return Citations
- Modify `_query_bedrock()` in `chatbot/handlers/bedrock_kb_handler.py`
- Return the full `response['citations']` array in addition to current return values
- Update return dict to include: `output_text`, `session_id`, `turn_count`, `citations`

### 2. Add `_extract_citations()` Method
- Add new method `_extract_citations(self, citations: list) -> list` to `BedrockKBHandler`
- Extract S3 URIs from `citations[].retrievedReferences[].location.s3Location.uri`
- Parse filename from URI using `uri.split('/')[-1]`
- Return list of source dicts with keys: `doc`, `pages` (empty list), `url` (empty string)
- Mirror the implementation in `evaluation/bedrock_evaluator.py:68-85`

### 3. Update `_parse_response()` to Only Extract Answer
- Modify `_parse_response()` to only extract the ANSWER section from LLM output
- Remove all SOURCES parsing logic (lines 73-88)
- Simplify return type to just `str` (answer text only)
- Handle case where ANSWER: section is not present (return full text)

### 4. Update `handle()` and `handle_async()` Methods
- Update both methods to use `_extract_citations()` with API response citations
- Change `answer, sources = self._parse_response(...)` to `answer = self._parse_response(...)`
- Add `sources = self._extract_citations(result['citations'])`
- Ensure sources come from API, not parsed text

### 5. Simplify the Bedrock Agent Prompt
- Edit `chatbot/prompts/bedrock_agent_prompt.py`
- Remove the OUTPUT FORMAT section with SOURCES instructions (lines 41-55)
- Keep only the ANSWER instruction: "Your response should be clear and concise"
- This prevents LLM from including bogus SOURCES in output text

### 6. Update Tests for Citation Accuracy
- Modify `tests/test_bedrock_kb_handler.py`
- Update `test_response_parsing()` to verify source filenames match KB filename pattern
- Add assertion: source filenames should be lowercase with dashes (e.g., `*-twc.pdf`, `*-hhsc.pdf`)
- Add assertion: source filenames should NOT contain spaces or capital letters
- Add new test `test_citations_are_real_kb_filenames()` that queries and validates citation format

### 7. Add Integration Test for Citation Validation
- Add new test class `TestBedrockKBCitations` to `tests/test_bedrock_kb_handler.py`
- Test method `test_citations_match_kb_filename_pattern()`:
  - Query handler with a question that returns sources
  - Verify each source doc follows pattern: lowercase, dashes, ends with `.pdf`
  - Verify no spaces or invented titles in filenames
- Test method `test_no_hallucinated_citations()`:
  - Query with debug=True
  - Verify `raw_output` may contain ANSWER/SOURCES but `response['sources']` comes from API

### 8. Run Validation Commands
- Run all validation commands listed below
- Verify all tests pass
- Verify citation format is correct in debug output

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

```bash
# 1. Run unit tests for the handler
pytest tests/test_bedrock_kb_handler.py -v

# 2. Test citation format manually - should show lowercase-dash filenames
python -c "
from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
handler = BedrockKBHandler()
response = handler.handle('What is the income limit for a family of 4?', debug=True)
print('=== SOURCES ===')
for s in response['sources']:
    print(f\"  - {s['doc']}\")
print()
print('=== RAW OUTPUT (first 500 chars) ===')
print(response['debug_info']['raw_output'][:500])
"

# 3. Verify no hallucinated filenames (should NOT contain spaces or capital letters)
python -c "
from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
handler = BedrockKBHandler()
response = handler.handle('What is TWC?', debug=True)
for s in response['sources']:
    doc = s['doc']
    assert ' ' not in doc, f'Hallucinated filename (has spaces): {doc}'
    assert doc == doc.lower(), f'Hallucinated filename (has capitals): {doc}'
    print(f'✓ Valid: {doc}')
print('All citations are valid KB filenames!')
"

# 4. Run full test suite to check for regressions
pytest tests/ -v -k "bedrock"

# 5. Verify async handler also uses correct citations
python -c "
import asyncio
from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
handler = BedrockKBHandler()
response = asyncio.run(handler.handle_async('What is CCS?'))
for s in response['sources']:
    doc = s['doc']
    assert ' ' not in doc, f'Async: Hallucinated filename: {doc}'
    print(f'✓ Async valid: {doc}')
"
```

## Notes
- The `BedrockKBEvaluator` already correctly extracts citations from the API response - use it as a reference implementation
- The `$search_results$` placeholder in Bedrock's prompt template does NOT expose filename metadata to the LLM - this is a fundamental limitation of Bedrock's API
- After the fix, the LLM may still output a SOURCES section in the text (until prompt is updated), but the handler will ignore it and use API citations instead
- The prompt simplification (Step 5) is optional but recommended to prevent confusion and reduce token usage
- Consider adding debug logging to track when citations are extracted to help with future debugging
