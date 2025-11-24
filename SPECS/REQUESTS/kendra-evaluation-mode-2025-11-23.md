# Feature Request: Kendra Evaluation Mode

**Date:** 2025-11-23
**Status:** Implemented

## Overview
Add Amazon Kendra as a 4th retrieval mode for both interactive chatbot and automated evaluation, enabling comparison against existing hybrid/dense/openai modes.

## Problem Statement
Need to evaluate Amazon Kendra's retrieval quality against the existing Qdrant-based retrieval using the same Q&A test suite and scoring framework.

## Users & Stakeholders
- Primary Users: Developers comparing retrieval strategies
- Permissions: AWS credentials with Kendra and Bedrock access

## Functional Requirements

1. **KendraHandler**: New handler implementing the same interface as RAGHandler
   - Uses `AmazonKendraRetriever` from langchain-aws
   - Uses `ChatBedrockConverse` with Titan for generation
   - No reranking step (Kendra handles relevance internally)

2. **Evaluation Mode**: `--mode kendra` works with existing evaluation framework
   - Writes results to `results/kendra/` (isolated from other modes)
   - Supports all existing flags: `--resume`, `--limit`, `--debug`, etc.

3. **Interactive Chat**: Kendra mode available via:
   - Environment variable: `RETRIEVAL_MODE=kendra`
   - CLI flag: `python interactive_chat.py --mode kendra`

4. **Source Mapping**: Map Kendra metadata to existing format
   - `doc`: Kendra `source` or `title`
   - `page`: Kendra page number if available, else null
   - `url`: Kendra `source_uri` if available

## User Flow

### Evaluation
```bash
# Run Kendra evaluation
python -m evaluation.run_evaluation --mode kendra

# Compare with other modes (parallel)
python -m evaluation.run_evaluation --mode hybrid &
python -m evaluation.run_evaluation --mode kendra &
```

### Interactive Chat
```bash
# Via environment variable
export RETRIEVAL_MODE=kendra
python interactive_chat.py

# Via CLI flag
python interactive_chat.py --mode kendra
```

## Acceptance Criteria
- [ ] `python -m evaluation.run_evaluation --mode kendra` runs successfully
- [ ] Results written to `results/kendra/` directory
- [ ] Checkpoint/resume works for kendra mode
- [ ] `python interactive_chat.py --mode kendra` launches Kendra-backed chat
- [ ] Sources mapped to `doc`/`page`/`url` format for judge scoring
- [ ] Evaluation judge can score Kendra responses (all 4 criteria)

## Technical Requirements

### Integration
- **langchain-aws**: `AmazonKendraRetriever`, `ChatBedrockConverse`
- **AWS Services**: Kendra (retrieval), Bedrock (Titan generation)

### Configuration (Hardcoded)
```python
KENDRA_INDEX_ID = "4aee3b7a-0217-4ce5-a0a2-b737cda375d9"
KENDRA_REGION = "us-east-1"
BEDROCK_MODEL = "amazon.titan-text-express-v1"
KENDRA_TOP_K = 5
```

### AWS Credentials
Standard AWS credential chain:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- `~/.aws/credentials` file
- IAM role (if running on AWS)

### Performance
- No specific requirements beyond existing evaluation timeouts (30s)

## Architecture

```
evaluation/run_evaluation.py
    ↓ (--mode kendra)
KendraEvaluator (new)
    ↓
KendraHandler (new)
    ├─→ AmazonKendraRetriever (retrieval)
    └─→ ChatBedrockConverse/Titan (generation)
    ↓
LLMJudge (existing - unchanged)
    ↓
Reporter (existing - writes to results/kendra/)
```

## Files to Create/Modify

### New Files
1. `chatbot/handlers/kendra_handler.py` - Kendra retrieval + Bedrock generation
2. `evaluation/kendra_evaluator.py` - Wrapper for evaluation framework

### Modify
1. `chatbot/config.py` - Add Kendra constants
2. `evaluation/config.py` - Add 'kendra' to VALID_MODES
3. `evaluation/run_evaluation.py` - Route to KendraEvaluator when mode=kendra
4. `interactive_chat.py` - Support `--mode` flag, route to KendraHandler
5. `chatbot/intent_router.py` - Route to KendraHandler when mode=kendra

## Edge Cases & Error Handling

1. **AWS credentials missing** → Clear error message with setup instructions
2. **Kendra index unavailable** → Fail fast with connection error
3. **Bedrock model access denied** → Error message about model access
4. **No results from Kendra** → Return empty sources, let judge score accordingly
5. **Kendra metadata missing fields** → Use sensible defaults (null for page, "Unknown" for doc)

## Dependencies

### Requires
- `langchain-aws` package (add to requirements.txt if not present)
- AWS credentials configured
- Kendra index populated with same PDFs

### Blocks
- Nothing

## Out of Scope
- Kendra index creation/management
- PDF ingestion to Kendra (assumed already done)
- Configurable Kendra settings (hardcoded for prototype)
- Reranking after Kendra retrieval

## Success Metrics
- Kendra evaluation completes on full Q&A suite
- Can compare pass rates: hybrid vs dense vs kendra vs openai
- Evaluation results parseable by existing report format

## Notes
- Reference implementation: `AMAZON_EXPERIMENT/kendra_test.py`
- This is a prototype - configuration hardcoded for simplicity
- Kendra's internal ranking replaces our reranker step
