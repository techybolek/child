# Feature: Bedrock Knowledge Base Evaluator

## Feature Description
Add Amazon Bedrock Knowledge Bases as an evaluation mode alongside existing modes (hybrid, dense, openai, kendra, vertex). This enables comparative benchmarking of AWS's managed RAG solution against the custom pipeline implementation.

The Bedrock KB evaluator will query a pre-configured Knowledge Base (ID: `371M2G58TV`) that uses OpenSearch Serverless as its vector store, Titan Text Embeddings V2 for embeddings, and default chunking (~300 tokens). Generation will use Claude 3 Haiku for fast, cost-effective responses.

## User Story
As a developer evaluating RAG solutions
I want to benchmark Bedrock Knowledge Bases against my custom RAG pipeline
So that I can quantify the value of custom contextual embeddings, hybrid search, and adaptive reranking

## Problem Statement
The current evaluation framework supports hybrid, dense, openai, kendra, and vertex modes, but lacks support for Amazon Bedrock Knowledge Bases - AWS's newest managed RAG offering. Without this comparison, it's difficult to demonstrate the ROI of the custom 3-tier contextual embedding pipeline versus AWS's "upload and go" solution.

## Solution Statement
Implement a `BedrockKBEvaluator` class following the established evaluator pattern (similar to `KendraEvaluator`, `OpenAIEvaluator`, `VertexAgentEvaluator`). The evaluator will:
1. Use `boto3` client `bedrock-agent-runtime` to call `retrieve_and_generate`
2. Extract answer text and source citations from the response
3. Return results in the standard evaluator format expected by `BatchEvaluator`
4. Integrate with the existing CLI via `--mode bedrock`

## Relevant Files
Use these files to implement the feature:

### Files to Modify
- `evaluation/config.py` - Add 'bedrock' to `VALID_MODES` list
- `evaluation/run_evaluation.py` - Add bedrock case in evaluator selection block (~line 93-99)

### Files for Reference (Patterns)
- `evaluation/kendra_evaluator.py` - Similar AWS evaluator pattern, uses boto3 (33 lines)
- `evaluation/vertex_evaluator.py` - External API evaluator pattern (31 lines)
- `evaluation/openai_evaluator.py` - Handler-based evaluator pattern (31 lines)
- `tests/test_evaluation_e2e_kendra.py` - E2E test pattern for AWS evaluators
- `tests/test_evaluation_e2e_vertex.py` - E2E test with credential check pattern

### New Files
- `evaluation/bedrock_evaluator.py` - New Bedrock KB evaluator class
- `tests/test_evaluation_e2e_bedrock.py` - E2E test for bedrock mode

## Implementation Plan

### Phase 1: Foundation
- Review existing evaluator patterns to ensure consistency
- Verify boto3 is available (already installed for Kendra)
- Confirm AWS credentials work for Bedrock (same credentials as Kendra)

### Phase 2: Core Implementation
- Create `BedrockKBEvaluator` class with `query()` method
- Implement `retrieve_and_generate` API call to Bedrock Knowledge Base
- Parse response to extract answer and source citations
- Handle the fact that Bedrock doesn't preserve page numbers (set to 'N/A')

### Phase 3: Integration
- Add 'bedrock' to `VALID_MODES` in config
- Add bedrock case in `run_evaluation.py` evaluator selection
- Create E2E test following existing patterns
- Validate end-to-end flow with sanity questions

## Step by Step Tasks

### Step 1: Create BedrockKBEvaluator Class
- Create `evaluation/bedrock_evaluator.py`
- Implement `BedrockKBEvaluator` class with:
  - `__init__`: Initialize boto3 client, KB ID, model ARN
  - `query(question, debug)`: Call `retrieve_and_generate`, return standardized response
- Follow the pattern from `kendra_evaluator.py` and `vertex_evaluator.py`
- Use environment variables: `BEDROCK_KB_ID` (default: `371M2G58TV`), `AWS_REGION` (default: `us-east-1`)

### Step 2: Update Configuration
- Edit `evaluation/config.py`:
  - Add `'bedrock'` to `VALID_MODES` list

### Step 3: Integrate with Run Script
- Edit `evaluation/run_evaluation.py`:
  - Add `elif mode == 'bedrock':` case after the vertex case (~line 99)
  - Import `BedrockKBEvaluator` from `.bedrock_evaluator`
  - Instantiate evaluator and set `custom_evaluator`
  - Print: `"Evaluator: Amazon Bedrock Knowledge Base (Titan Embeddings + Claude Haiku)"`

### Step 4: Create E2E Test
- Create `tests/test_evaluation_e2e_bedrock.py`
- Follow pattern from `test_evaluation_e2e_vertex.py`:
  - Add `bedrock_configured()` function to check AWS credentials
  - Use singleton pattern for evaluation result
  - Test: evaluation completes, artifacts created, results format, summary stats, pass rate
  - Skip tests if AWS credentials not configured
- Use `MODE = "bedrock"`, `RUN_NAME = "TEST_BEDROCK"`
- Set `MIN_PASS_SCORE = 50.0` (lower threshold for managed solution)
- Extended timeout (600s) for API latency

### Step 5: Run Validation Commands
- Execute all validation commands to verify the implementation works correctly with zero regressions

## Testing Strategy

### Unit Tests
- No unit tests needed - the evaluator is a thin wrapper around AWS API
- AWS API calls should not be mocked (per project guidelines)

### Integration Tests
- E2E test (`tests/test_evaluation_e2e_bedrock.py`) validates:
  - Evaluation completes without errors
  - All output artifacts are created (JSONL, JSON, TXT)
  - Results have correct structure and required fields
  - Summary statistics are valid
  - No checkpoint left on success

### Edge Cases
- AWS credentials not configured - skip tests gracefully
- Bedrock KB returns empty response - handle gracefully
- Network timeout - boto3 handles retries
- Invalid KB ID - boto3 raises appropriate exception

## Acceptance Criteria
1. `python -m evaluation.run_evaluation --mode bedrock --test --limit 3` completes successfully
2. Results saved to `results/bedrock/RUN_<timestamp>/` directory
3. All three output files created: `detailed_results.jsonl`, `evaluation_summary.json`, `evaluation_report.txt`
4. E2E test passes: `pytest tests/test_evaluation_e2e_bedrock.py -v`
5. Existing tests still pass (no regressions)
6. CLI help shows 'bedrock' as valid mode choice

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `python -m evaluation.run_evaluation --mode bedrock --test --limit 3` - Quick evaluation test with Bedrock KB
- `python -m evaluation.run_evaluation --mode bedrock --file test-sanity-qa.md --debug` - Debug mode with sanity questions
- `pytest tests/test_evaluation_e2e_bedrock.py -v` - Run E2E test for bedrock mode
- `pytest tests/test_evaluation_e2e.py tests/test_evaluation_e2e_kendra.py -v` - Verify existing tests still pass
- `python -m evaluation.run_evaluation --help` - Verify 'bedrock' appears in mode choices

## Notes

1. **No page numbers** - Bedrock KB doesn't preserve PDF page metadata in citations, so sources will show `page: N/A`. This is a known limitation of the managed service.

2. **Model choice** - Using Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) for generation. Fast and cheap. Can switch to Sonnet for better quality if needed.

3. **boto3 already installed** - Used by Kendra evaluator, no new dependencies needed.

4. **AWS credentials** - Same credentials used for Kendra work for Bedrock. Requires `bedrock-agent-runtime` permissions.

5. **Comparison value** - This evaluator will benchmark the custom pipeline (3-tier contextual embeddings + hybrid search + adaptive reranking) against AWS's managed solution with:
   - Default chunking (~300 tokens vs 1000 chars)
   - Titan embeddings (dense only vs hybrid)
   - No custom reranking
   - No contextual enrichment

6. **Expected performance** - The custom pipeline should outperform Bedrock KB on nuanced questions, especially those requiring table data or cross-document reasoning. Bedrock KB may perform comparably on simple factual questions.
