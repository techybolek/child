# Feature Request: Parallel Evaluation Mode Support

**Date:** 2025-11-23
**Status:** Refined

## Overview

Enable running evaluation in three modes (`hybrid`, `dense`, `openai`) simultaneously without interference by isolating results and checkpoints into mode-specific subdirectories.

## Problem Statement

Currently, all evaluation runs save results to the same `results/` directory with a single `checkpoint.json`. This causes:
1. File overwrites when running multiple modes in parallel
2. Checkpoint conflicts (one mode's checkpoint overwrites another's)
3. No clear separation of results by retrieval strategy

Additionally, the hybrid/dense mode is controlled by a boolean flag (`ENABLE_HYBRID_RETRIEVAL`) in config rather than an explicit mode selection.

## Users & Stakeholders

- **Primary Users**: Developers running comparative evaluations across retrieval strategies
- **Use Case**: Launch 3 terminals, run each mode simultaneously, compare results

## Functional Requirements

### 1. CLI Mode Flag
Replace `--openai-agent` with unified `--mode` flag:
```bash
python -m evaluation.run_evaluation --mode hybrid
python -m evaluation.run_evaluation --mode dense
python -m evaluation.run_evaluation --mode openai
```

### 2. Mode-Specific Output Directories
```
results/
├── hybrid/
│   ├── detailed_results_20251123_143022.jsonl
│   ├── evaluation_summary_20251123_143022.json
│   ├── evaluation_report_20251123_143022.txt
│   ├── failure_analysis_20251123_143022.txt
│   ├── checkpoint.json
│   └── debug_eval.txt
├── dense/
│   └── ... (same structure)
└── openai/
    └── ... (same structure)
```

### 3. Config Change: `RETRIEVAL_MODE`
In `chatbot/config.py`, replace:
```python
# OLD
ENABLE_HYBRID_RETRIEVAL = True

# NEW
RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'hybrid')  # 'hybrid', 'dense', 'openai'
```

### 4. Default Mode from Config
When `--mode` is not specified, evaluation reads default from `chatbot/config.py`:
```python
from chatbot import config
default_mode = config.RETRIEVAL_MODE
```

### 5. Auto-Resume Latest Checkpoint
When using `--resume --mode <mode>`:
- Automatically find and load `results/<mode>/checkpoint.json`
- No need to specify run timestamp

## User Flow

### Running Parallel Evaluations
```bash
# Terminal 1
python -m evaluation.run_evaluation --mode hybrid

# Terminal 2
python -m evaluation.run_evaluation --mode dense

# Terminal 3
python -m evaluation.run_evaluation --mode openai
```

### Resuming After Failure
```bash
# Resume hybrid mode (auto-finds results/hybrid/checkpoint.json)
python -m evaluation.run_evaluation --mode hybrid --resume

# Resume and test just the failed question
python -m evaluation.run_evaluation --mode hybrid --resume --resume-limit 1
```

## Acceptance Criteria

- [ ] `--mode` flag accepts `hybrid`, `dense`, `openai`
- [ ] Without `--mode`, defaults to `chatbot.config.RETRIEVAL_MODE`
- [ ] Each mode writes to `results/<mode>/` subdirectory
- [ ] Checkpoints isolated per mode (`results/<mode>/checkpoint.json`)
- [ ] `--resume` auto-loads checkpoint from mode's directory
- [ ] Three modes can run simultaneously without conflicts
- [ ] `--openai-agent` flag removed (replaced by `--mode openai`)
- [ ] `chatbot/config.py` uses `RETRIEVAL_MODE` instead of `ENABLE_HYBRID_RETRIEVAL`
- [ ] Backward compatibility: code using old `ENABLE_HYBRID_RETRIEVAL` gets deprecation warning or breaks cleanly

## Technical Requirements

### Files to Modify

| File | Changes |
|------|---------|
| `chatbot/config.py` | Replace `ENABLE_HYBRID_RETRIEVAL` with `RETRIEVAL_MODE` |
| `chatbot/retriever.py` | Update to use `RETRIEVAL_MODE` |
| `chatbot/handlers/rag_handler.py` | Update retriever selection logic |
| `evaluation/run_evaluation.py` | Add `--mode` flag, remove `--openai-agent` |
| `evaluation/batch_evaluator.py` | Pass mode to Reporter, update checkpoint path |
| `evaluation/reporter.py` | Use mode-specific output directory |
| `evaluation/config.py` | Add `get_results_dir(mode)` helper |

### Mode → Evaluator Mapping

```python
MODE_EVALUATORS = {
    'hybrid': lambda: ChatbotEvaluator(retrieval_mode='hybrid'),
    'dense': lambda: ChatbotEvaluator(retrieval_mode='dense'),
    'openai': lambda: OpenAIAgentEvaluator()
}
```

### ChatbotEvaluator Changes

```python
class ChatbotEvaluator:
    def __init__(self, collection_name=None, retrieval_top_k=None, retrieval_mode=None):
        # retrieval_mode overrides config if provided
        self.handler = RAGHandler(
            collection_name=collection_name,
            retrieval_top_k=retrieval_top_k,
            retrieval_mode=retrieval_mode  # NEW: explicit mode override
        )
```

### Directory Creation

```python
def get_results_dir(mode: str) -> Path:
    """Get mode-specific results directory, creating if needed"""
    results_dir = Path('results') / mode
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir
```

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| Invalid mode value | Error: "Invalid mode 'X'. Choose from: hybrid, dense, openai" |
| `--resume` without existing checkpoint | Error: "No checkpoint found for mode 'X'" |
| Mode directory doesn't exist | Create automatically on first run |
| Old `results/checkpoint.json` exists | Ignore (legacy file, doesn't affect new mode dirs) |

## Dependencies

- **Requires**: Existing evaluation system, OpenAI agent in `OAI_EXPERIMENT/`
- **Blocks**: None

## Out of Scope

- Cross-mode comparison reports (aggregating results from all three modes)
- Nested run directories within mode subdirs
- Explicit run ID for resume (uses latest checkpoint only)
- Migration script for existing `results/` files

## Success Metrics

- Can launch 3 evaluation processes simultaneously without errors
- Each mode's results cleanly separated in filesystem
- Resume works correctly per-mode

## Notes

- The `openai` mode uses a completely different RAG system (`OAI_EXPERIMENT/agent1.py` with GPT-5 + FileSearch)
- `hybrid` and `dense` modes both use the same Qdrant collection but different retrieval strategies
- Environment variable `RETRIEVAL_MODE` allows override without code changes
