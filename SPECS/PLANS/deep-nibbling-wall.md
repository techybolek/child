# Bug: run_info.txt Dumps All Mode Parameters Instead of Mode-Specific Configuration

## Bug Description

The evaluation system generates `run_info.txt` for each evaluation mode (hybrid, dense, openai, kendra), but the configuration writer (`run_info_writer.py`) blindly dumps all parameters from `chatbot/config.py`, regardless of which mode is running. This results in:

1. **Kendra mode** showing Qdrant collection/retrieval parameters (which it doesn't use)
2. **Dense mode** showing the same config as hybrid mode (but hybrid uses additional RRF fusion parameters)
3. **Hybrid mode** NOT showing its specific parameters (FUSION_METHOD, RRF_K, HYBRID_PREFETCH_LIMIT, BM25_VOCABULARY_SIZE)
4. **All modes** showing identical LLM/reranker configs even though openai and kendra use different systems

**Expected behavior**: Each mode's `run_info.txt` should only display configuration parameters relevant to that specific mode.

**Actual behavior**: All modes dump the same static chatbot config parameters, making it impossible to understand what each mode actually used during evaluation.

## Problem Statement

The `write_run_info()` function in `evaluation/run_info_writer.py` receives the `mode` parameter but doesn't use it to filter or customize the configuration output. It simply imports three config modules and dumps their values without considering:
- Which retriever is actually being used (hybrid vs dense vs kendra vs openai)
- Which parameters are relevant to each mode
- Which external systems are being used (AWS Kendra, OpenAI Agent)

## Solution Statement

Refactor `write_run_info()` to output mode-specific configuration sections:
1. **Shared sections** (all modes): Judge settings, citation scoring
2. **Mode-specific sections**: Only display parameters relevant to the active mode
3. **Conditional sections**: Hide irrelevant parameters (e.g., Qdrant config for kendra mode)

Use conditional logic based on the `mode` parameter to determine which configuration sections to write.

## Steps to Reproduce

```bash
# Run evaluations for different modes
python -m evaluation.run_evaluation --mode dense --limit 1
python -m evaluation.run_evaluation --mode kendra --limit 1
python -m evaluation.run_evaluation --mode hybrid --limit 1

# Compare run_info.txt files
cat results/dense/RUN_*/run_info.txt
cat results/kendra/RUN_*/run_info.txt
cat results/hybrid/RUN_*/run_info.txt

# Observe: All three files show identical configuration except for "Mode:" field
```

## Root Cause Analysis

The bug originates in `evaluation/run_info_writer.py:8-61`:

```python
def write_run_info(results_dir: Path, mode: str):
    # Imports static config modules
    from chatbot import config as chatbot_config
    from evaluation import config as eval_config
    from LOAD_DB import config as load_config

    # Writes mode to header (CORRECT)
    f.write(f"Mode: {mode}\n")

    # But then dumps ALL chatbot config parameters (INCORRECT)
    f.write(f"Qdrant Collection: {chatbot_config.COLLECTION_NAME}\n")
    f.write(f"Generator Provider: {chatbot_config.LLM_PROVIDER}\n")
    # ... etc for ALL parameters regardless of mode
```

**Root cause**: The function has no conditional logic based on `mode`. It treats all modes as if they use the same retrieval system and LLM configuration.

**Mode-specific parameters that exist but aren't conditionally handled**:
- **Hybrid-only**: `FUSION_METHOD='rrf'`, `RRF_K=60`, `HYBRID_PREFETCH_LIMIT=100`, `BM25_VOCABULARY_SIZE=30000`
- **Kendra-only**: `KENDRA_INDEX_ID`, `KENDRA_REGION`, `BEDROCK_MODEL`, `KENDRA_TOP_K=5`
- **OpenAI-only**: External agent configuration (not in chatbot/config.py)

## Relevant Files

### Files to Modify

- **`evaluation/run_info_writer.py`** (lines 8-61)
  - Primary file to fix - add conditional logic based on `mode` parameter
  - Add mode-specific sections for hybrid, dense, kendra, openai
  - Hide irrelevant parameters for each mode

### Reference Files (Read-only)

- **`chatbot/config.py`** (lines 64-82)
  - Contains mode-specific parameters: FUSION_METHOD, RRF_K, HYBRID_PREFETCH_LIMIT, BM25_VOCABULARY_SIZE (hybrid)
  - Contains KENDRA_* parameters (kendra mode)
  - Shows which parameters are shared vs mode-specific

- **`evaluation/batch_evaluator.py`** (line 82)
  - Calls `write_run_info(self.run_dir, self.mode)` with correct mode parameter
  - No changes needed - already passing mode correctly

- **`evaluation/run_evaluation.py`** (lines 63-108)
  - Shows how mode determines which evaluator class is instantiated
  - Reference for understanding mode behavior

## Step by Step Tasks

### 1. Refactor write_run_info() with Mode-Specific Sections

**In `evaluation/run_info_writer.py`:**

- Add conditional logic to write different sections based on `mode` parameter
- Create helper function `_write_qdrant_config()` for hybrid/dense modes only
- Create helper function `_write_kendra_config()` for kendra mode only
- Create helper function `_write_hybrid_specific_config()` for hybrid mode only
- Keep shared sections (Judge, Citations) for all modes

**Structure:**
```
=== EVALUATION RUN CONFIGURATION ===
Mode: {mode}
Timestamp: {timestamp}

--- RETRIEVAL CONFIGURATION ---
[if mode in ['hybrid', 'dense']]
  Qdrant Collection: ...
  Embedding Model: ...
  Retrieval Top K: ...
  Rerank Top K: ...
  [if mode == 'hybrid']
    Fusion Method: rrf
    RRF K: 60
    Prefetch Limit: 100
    BM25 Vocabulary: 30000
  [endif]
[elif mode == 'kendra']
  Kendra Index ID: ...
  Kendra Region: ...
  Kendra Top K: ...
  Bedrock Model: ...
[elif mode == 'openai']
  OpenAI Agent: gpt-5 with FileSearch
  (Note: External configuration)
[endif]

--- LLM MODELS ---
[if mode in ['hybrid', 'dense']]
  Generator Provider: ...
  Generator Model: ...
  Reranker Provider: ...
  Reranker Model: ...
  Intent Classifier Provider: ...
  Intent Classifier Model: ...
[elif mode == 'kendra']
  Generator: Bedrock {BEDROCK_MODEL}
[elif mode == 'openai']
  Generator: OpenAI gpt-5
[endif]

--- EVALUATION SETTINGS ---
[all modes]
Judge Provider: ...
Judge Model: ...
Citations Enabled: ...
```

### 2. Add Mode Documentation Section

**In `evaluation/run_info_writer.py`:**

- Add a "MODE DESCRIPTION" section explaining what the mode does
- Hybrid: "Dense + sparse vectors with RRF fusion"
- Dense: "Dense-only semantic search"
- Kendra: "AWS Kendra enterprise search with Bedrock LLM"
- OpenAI: "OpenAI GPT-5 agent with FileSearch tool"

### 3. Test All Four Modes

**Run evaluations for each mode and verify run_info.txt:**

```bash
# Test each mode with single question
python -m evaluation.run_evaluation --mode hybrid --limit 1
python -m evaluation.run_evaluation --mode dense --limit 1
python -m evaluation.run_evaluation --mode kendra --limit 1
python -m evaluation.run_evaluation --mode openai --limit 1

# Verify each run_info.txt shows correct mode-specific config
cat results/hybrid/RUN_*/run_info.txt
cat results/dense/RUN_*/run_info.txt
cat results/kendra/RUN_*/run_info.txt
cat results/openai/RUN_*/run_info.txt
```

**Expected differences:**
- Hybrid: Shows RRF fusion parameters (FUSION_METHOD, RRF_K, PREFETCH_LIMIT, BM25_VOCABULARY_SIZE)
- Dense: Shows Qdrant config but NO RRF parameters
- Kendra: Shows Kendra/Bedrock config, NO Qdrant parameters
- OpenAI: Shows OpenAI agent config, NO Qdrant/Kendra parameters

### 4. Update Documentation

**In `SPECS/evaluation_system.md`:**

- Update the "Output Format" section to document mode-specific run_info.txt structure
- Add examples of run_info.txt for each mode
- Document which parameters appear in which modes

## Validation Commands

Execute every command to validate the bug is fixed with zero regressions:

```bash
# 1. Run evaluation for each mode (test with 1 question each)
python -m evaluation.run_evaluation --mode hybrid --limit 1
python -m evaluation.run_evaluation --mode dense --limit 1
python -m evaluation.run_evaluation --mode kendra --limit 1
python -m evaluation.run_evaluation --mode openai --limit 1

# 2. Verify each run_info.txt is mode-specific
# Hybrid should show: FUSION_METHOD, RRF_K, HYBRID_PREFETCH_LIMIT, BM25_VOCABULARY_SIZE
cat results/hybrid/RUN_*/run_info.txt | grep -E "Fusion|RRF|Prefetch|BM25"

# Dense should NOT show RRF parameters but should show Qdrant config
cat results/dense/RUN_*/run_info.txt | grep -v "Fusion\|RRF\|Prefetch\|BM25" | grep "Qdrant"

# Kendra should show KENDRA_INDEX_ID, BEDROCK_MODEL, not Qdrant
cat results/kendra/RUN_*/run_info.txt | grep -E "Kendra|Bedrock"
cat results/kendra/RUN_*/run_info.txt | grep -v "Qdrant"

# OpenAI should show OpenAI agent info, not Qdrant or Kendra
cat results/openai/RUN_*/run_info.txt | grep "OpenAI"
cat results/openai/RUN_*/run_info.txt | grep -v "Qdrant\|Kendra"

# 3. Verify all modes still show shared config (Judge, Citations)
for mode in hybrid dense kendra openai; do
  echo "=== $mode ==="
  cat results/$mode/RUN_*/run_info.txt | grep -E "Judge|Citations"
done

# 4. Run full evaluation for one mode to ensure no regressions
python -m evaluation.run_evaluation --mode hybrid --limit 5
```

## Notes

**Design Decision: Keep It Minimal**

The fix should be surgical - only modify `run_info_writer.py`. No changes to:
- `batch_evaluator.py` (already passes mode correctly)
- `run_evaluation.py` (mode selection logic is correct)
- Config files (parameters are correctly organized)

**Mode-Specific Parameter Reference**

From `chatbot/config.py`:

**Hybrid-specific (lines 69-72):**
- `FUSION_METHOD = 'rrf'`
- `RRF_K = 60`
- `HYBRID_PREFETCH_LIMIT = 100`
- `BM25_VOCABULARY_SIZE = 30000`

**Kendra-specific (lines 79-82):**
- `KENDRA_INDEX_ID = "4aee3b7a-0217-4ce5-a0a2-b737cda375d9"`
- `KENDRA_REGION = "us-east-1"`
- `BEDROCK_MODEL = "openai.gpt-oss-20b-1:0"`
- `KENDRA_TOP_K = 5`

**Shared (both hybrid and dense):**
- `COLLECTION_NAME`, `RETRIEVAL_TOP_K`, `RERANK_TOP_K`
- `LLM_PROVIDER`, `LLM_MODEL`, `RERANKER_*`, `INTENT_CLASSIFIER_*`

**OpenAI mode:**
- Uses external agent (no chatbot/config.py parameters)
- Configuration in `OAI_EXPERIMENT/agent1.py` (not exposed to evaluation)
