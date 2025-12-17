# Bug: Bedrock KB Returns No Citations With Custom Prompt

## Bug Description
After implementing the citation hallucination fix (which correctly extracts citations from the API response instead of parsing LLM text), the `BedrockKBHandler` returns **no citations at all**.

**Observed Behavior:**
- Handler response contains `sources: []` (empty list)
- API `response['citations']` contains 1 citation with 0 `retrievedReferences`

**Expected Behavior:**
- Handler should return actual S3 filenames like `3202600043-eccs-rfp-twc.pdf`
- API should populate `retrievedReferences` with source documents

## Problem Statement
The custom prompt template in `BedrockKBHandler._query_bedrock()` is missing the `$output_format_instructions$` placeholder variable that Bedrock requires for citations to work. Without this placeholder, Bedrock doesn't include its internal citation formatting instructions, causing the `retrievedReferences` array to remain empty.

## Solution Statement
Add the `$output_format_instructions$` placeholder to the custom prompt template in `BedrockKBHandler`. This placeholder contains Bedrock's internal instructions that tell the model how to format citations. The fix is a single-line change to the prompt template string.

## Steps to Reproduce
1. Start the FastAPI backend with `bedrock_agent` mode enabled
2. Send a query via the chat API: `POST /api/chat` with `mode: "bedrock_agent"`
3. Observe the response: `sources` array is empty
4. Check debug info: `citations` array has 1 entry but `retrievedReferences` is empty

Or run the validation command:
```bash
python -c "
from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
handler = BedrockKBHandler()
response = handler.handle('What is TWC?', debug=True)
print(f'Sources: {len(response[\"sources\"])}')
print(f'Debug citations: {response[\"debug_info\"].get(\"raw_output\", \"\")[:200]}')
"
```

## Root Cause Analysis
The Bedrock `retrieve_and_generate` API uses placeholder variables in custom prompt templates:
- `$query$` - The user's question
- `$search_results$` - Retrieved chunks from the knowledge base
- `$output_format_instructions$` - Bedrock's internal citation formatting instructions

**Current (broken) template in `bedrock_kb_handler.py:130`:**
```python
'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
```

**Required (working) template:**
```python
'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
```

Without `$output_format_instructions$`, Bedrock doesn't know how to format citation markers in the response, and consequently doesn't populate the `retrievedReferences` array in the API response.

**Evidence from testing:**
| Configuration | Citations | retrievedReferences |
|---------------|-----------|---------------------|
| No custom prompt | 7 | 8 |
| Custom prompt WITHOUT `$output_format_instructions$` | 1 | 0 |
| Custom prompt WITH `$output_format_instructions$` | 3 | 11 |

## Relevant Files
Use these files to fix the bug:

- **`chatbot/handlers/bedrock_kb_handler.py`** - Contains the `_query_bedrock()` method with the broken prompt template at line 130. This is the primary file to fix.
- **`chatbot/prompts/bedrock_agent_prompt.py`** - Contains `BEDROCK_AGENT_PROMPT` constant. No changes needed here, but understanding its structure helps contextualize the fix.
- **`tests/test_bedrock_kb_handler.py`** - Contains existing tests for the handler including `TestBedrockKBCitations` class. Add a new test to verify citations are returned.
- **`SPECS/ISSUES/bedrock_missing_citations.md`** - The issue documentation with evidence and validation commands.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Fix the prompt template in BedrockKBHandler
- Open `chatbot/handlers/bedrock_kb_handler.py`
- Locate line 130 in the `_query_bedrock()` method
- Change the `textPromptTemplate` value from:
  ```python
  'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
  ```
  To:
  ```python
  'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
  ```

### 2. Add regression test to verify citations are returned
- Open `tests/test_bedrock_kb_handler.py`
- Add a new test method in `TestBedrockKBCitations` class:
  ```python
  def test_citations_returned_with_custom_prompt(self):
      """Test that citations are returned when using custom prompt template.

      Regression test for: Bedrock KB returns no citations with custom prompt
      Root cause: Missing $output_format_instructions$ placeholder in template.
      """
      handler = BedrockKBHandler()

      response = handler.handle("What is TWC?")

      # With the fix, we should get at least 1 source
      # Note: May vary by query, but "What is TWC?" should always return sources
      assert len(response['sources']) > 0, (
          "Expected sources from Bedrock KB. "
          "If empty, check that $output_format_instructions$ is in the prompt template."
      )
  ```

### 3. Verify the fix with validation commands
- Run the validation commands in the `Validation Commands` section below to confirm the bug is fixed.

### 4. Update issue status
- Open `SPECS/ISSUES/bedrock_missing_citations.md`
- Change status from `**Open**` to `**Resolved**`
- Add resolution date and commit reference

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

```bash
# 1. Quick validation - verify citations are returned (should show Sources > 0)
python -c "
from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
handler = BedrockKBHandler()
response = handler.handle('What is TWC?')
sources = response['sources']
print(f'Sources returned: {len(sources)}')
for s in sources:
    print(f'  - {s[\"doc\"]}')
assert len(sources) > 0, 'FAIL: No sources returned - bug not fixed'
print('PASS: Citations are returned')
"

# 2. Run the specific citation tests
pytest tests/test_bedrock_kb_handler.py::TestBedrockKBCitations -v

# 3. Run all Bedrock handler tests (ensure no regressions)
pytest tests/test_bedrock_kb_handler.py -v

# 4. Run Bedrock integration tests (API endpoints)
pytest tests/test_bedrock_kb_integration.py -v

# 5. Run a quick evaluation to verify end-to-end (limit 3 questions)
python -m evaluation.run_evaluation --mode bedrock --test --limit 3
```

## Notes
- The fix is surgical: a single string change in the prompt template.
- The `$output_format_instructions$` placeholder is documented in AWS re:Post and Bedrock documentation.
- The `BedrockKBEvaluator` in `evaluation/bedrock_evaluator.py` does NOT use a custom prompt and therefore doesn't have this bug. No changes needed there.
- All existing tests should pass after the fix since they test response structure, not citation counts.
