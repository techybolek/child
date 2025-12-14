# Feature: Bedrock Knowledge Base Evaluator

## Feature Description
Add Amazon Bedrock Knowledge Bases as a new evaluation mode (`bedrock`) alongside existing modes (hybrid, dense, openai, kendra, vertex). This evaluator will query an existing Bedrock Knowledge Base (ID: `371M2G58TV`) backed by OpenSearch Serverless with Titan Text Embeddings V2, and use Claude Haiku for response generation.

This enables direct comparison between the custom RAG pipeline (3-tier contextual embeddings + hybrid search + adaptive reranking) and AWS's managed "upload and go" Knowledge Bases solution with default chunking, Titan embeddings, and no custom reranking.

## User Story
As a developer evaluating RAG system performance
I want to run evaluations against Amazon Bedrock Knowledge Bases
So that I can compare my custom RAG pipeline against AWS's managed solution

## Problem Statement
Currently, the evaluation system supports hybrid, dense, openai, kendra, and vertex modes. There's no way to evaluate against Amazon Bedrock Knowledge Bases, which represents AWS's managed RAG solution. Without this comparison, it's impossible to quantify the value-add of custom optimizations (contextual embeddings, hybrid search, adaptive reranking) versus a simple managed solution.

## Solution Statement
Create a `BedrockKBEvaluator` class that:
1. Uses `boto3` to call `bedrock-agent-runtime` API
2. Calls `retrieve_and_generate` endpoint with the configured Knowledge Base ID
3. Returns responses in the standard evaluator format (answer, sources, response_type, response_time)
4. Integrates with existing evaluation framework via `--mode bedrock`

The solution follows existing patterns established by `KendraEvaluator` and `OpenAIAgentEvaluator` - a standalone evaluator class with a `query()` method that returns a consistent response dictionary.

## Relevant Files
Use these files to implement the feature:

- `evaluation/config.py` - Contains `VALID_MODES` list that needs 'bedrock' added; provides patterns for constants and path utilities
- `evaluation/run_evaluation.py` - Contains `main()` with evaluator selection switch statement; needs new `elif mode == 'bedrock':` block
- `evaluation/kendra_evaluator.py` - Reference implementation for AWS-based evaluator; uses boto3 and returns standard response format
- `evaluation/openai_evaluator.py` - Another evaluator reference showing the consistent interface pattern
- `SPECS/evaluation_system.md` - Documentation to update with new bedrock mode

### New Files
- `evaluation/bedrock_evaluator.py` - New evaluator class for Bedrock Knowledge Bases

## Implementation Plan

### Phase 1: Foundation
Add 'bedrock' to the list of valid evaluation modes in the config. This enables the CLI argument parsing and mode validation without requiring the evaluator implementation.

### Phase 2: Core Implementation
Create `BedrockKBEvaluator` class following the established evaluator pattern:
- Initialize boto3 client for `bedrock-agent-runtime`
- Implement `query()` method using `retrieve_and_generate` API
- Extract answer text, citations/sources, and timing information
- Handle debug mode by including raw response

### Phase 3: Integration
Wire the new evaluator into `run_evaluation.py` by adding the bedrock case to the evaluator selection logic. Update documentation to reflect the new mode.

## Step by Step Tasks

### Step 1: Update Evaluation Config
- Open `evaluation/config.py`
- Add `'bedrock'` to the `VALID_MODES` list
- Result: `VALID_MODES = ['hybrid', 'dense', 'openai', 'kendra', 'vertex', 'bedrock']`

### Step 2: Create Bedrock Evaluator
- Create new file `evaluation/bedrock_evaluator.py`
- Import required modules: `os`, `time`, `boto3`
- Define `BedrockKBEvaluator` class with:
  - `__init__`: Initialize KB ID from env var (default: `371M2G58TV`), AWS region, boto3 client, model ARN
  - `query(question, debug)`: Call `retrieve_and_generate`, extract answer/sources, return standard format
- Follow exact response format from `KendraEvaluator`: `{'answer', 'sources', 'response_type', 'response_time'}`
- Sources should include `doc` (filename from S3 URI), `page` (N/A for Bedrock), `score`

### Step 3: Integrate into Run Evaluation
- Open `evaluation/run_evaluation.py`
- Locate the evaluator selection block (around line 80-110)
- Add new `elif mode == 'bedrock':` block after the `vertex` case
- Import `BedrockKBEvaluator` with try/except pattern for both relative and absolute imports
- Print evaluator description: "Evaluator: Amazon Bedrock Knowledge Base (Titan Embeddings + Claude Haiku)"

### Step 4: Update Documentation
- Open `SPECS/evaluation_system.md`
- Add `bedrock` to the Evaluation Modes table with description "Amazon Bedrock Knowledge Base"
- Update any mode lists to include bedrock

### Step 5: Test the Implementation
- Run basic test: `python -m evaluation.run_evaluation --mode bedrock --test --limit 1`
- Run debug mode: `python -m evaluation.run_evaluation --mode bedrock --debug --limit 3`
- Verify output directory created: `results/bedrock/RUN_*/`
- Check that sources are extracted correctly

### Step 6: Run Validation Commands
- Execute all validation commands listed below
- Fix any issues that arise
- Ensure zero regressions in existing modes

## Testing Strategy

### Unit Tests
- Test `BedrockKBEvaluator` initialization with default and custom KB ID
- Test response parsing logic (mocked boto3 response)
- Test source extraction from S3 URIs
- Test error handling for API failures

### Integration Tests
- Run `--mode bedrock --limit 1` to verify end-to-end flow
- Compare output structure with other evaluators
- Verify checkpoint/resume works with bedrock mode
- Verify reports generate correctly in `results/bedrock/`

### Edge Cases
- Missing AWS credentials - should raise clear error
- Invalid KB ID - should raise clear error
- Empty citations in response - should return empty sources list
- S3 URI without filename - should default to 'unknown' doc name
- API timeout/rate limiting - should propagate error appropriately

## Acceptance Criteria
- [ ] `--mode bedrock` is accepted by CLI argument parser
- [ ] `python -m evaluation.run_evaluation --mode bedrock --test --limit 1` completes successfully
- [ ] Results are saved to `results/bedrock/RUN_<timestamp>/`
- [ ] Response includes `answer`, `sources`, `response_type: 'bedrock_kb'`, `response_time`
- [ ] Sources contain `doc` (PDF filename), `page` (N/A), and `score`
- [ ] Debug mode shows raw API response
- [ ] Documentation updated to include bedrock mode
- [ ] Existing evaluation modes continue to work (no regressions)

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `python -c "from evaluation.config import VALID_MODES; assert 'bedrock' in VALID_MODES; print('Config OK')"` - Verify config updated
- `python -c "from evaluation.bedrock_evaluator import BedrockKBEvaluator; print('Import OK')"` - Verify evaluator imports
- `python -m evaluation.run_evaluation --mode bedrock --test --limit 1` - Basic bedrock evaluation test
- `python -m evaluation.run_evaluation --mode bedrock --debug --limit 1` - Test debug mode
- `python -m evaluation.run_evaluation --mode hybrid --test --limit 1` - Verify hybrid still works
- `python -m evaluation.run_evaluation --mode dense --test --limit 1` - Verify dense still works
- `ls results/bedrock/` - Verify bedrock results directory created

## Notes
- **No page numbers**: Bedrock KB doesn't preserve PDF page metadata, so sources will show `page: N/A`
- **Model choice**: Using Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) for generation - fast and cost-effective. Can switch to Sonnet for better quality.
- **boto3 dependency**: Already installed (used by Kendra evaluator) - no new dependencies needed
- **AWS credentials**: Same credentials used for Kendra should work; requires `bedrock-agent-runtime` permissions
- **Environment variable**: `BEDROCK_KB_ID` optional (defaults to `371M2G58TV`)
- **Comparison value**: Results will show impact of custom optimizations (3-tier context, hybrid search, adaptive reranking) vs AWS managed defaults
