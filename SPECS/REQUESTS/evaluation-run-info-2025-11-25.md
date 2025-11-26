# Feature Request: Evaluation Run Info File

**Date:** 2025-11-25
**Status:** Refined

## Overview
Add a `run_info.txt` file to each evaluation run directory that captures the key configuration parameters used to produce that specific evaluation run. This file serves as a configuration snapshot for reproducibility and debugging.

## Problem Statement
Currently, evaluation results are stored in mode-specific directories (`results/hybrid/`, `results/dense/`, `results/openai/`) but the specific configuration used to generate those results is not explicitly captured. When reviewing evaluation reports or comparing results across runs, it's difficult to know:
- Which models were used (LLM, reranker, intent classifier, judge)
- What retrieval parameters were configured (top_k, rerank_k)
- Which Qdrant collection was queried
- Whether citations were enabled or disabled

This makes it hard to reproduce results, debug issues, or understand what changed between evaluation runs.

## Users & Stakeholders
- **Primary Users**: Developers running evaluations, researchers analyzing results
- **Permissions**: No special permissions required (read-only file)

## Functional Requirements

1. Generate a `run_info.txt` file at the **start** of each evaluation run
2. Store the file in the mode-specific results directory: `results/<mode>/run_info.txt`
3. Capture the following **critical parameters**:
   - **Mode**: Retrieval mode (hybrid/dense/openai)
   - **LLM Model**: Generator model name and provider
   - **Reranker Model**: Reranker model name and provider
   - **Intent Classifier Model**: Intent classifier model name and provider
   - **Embedding Model**: OpenAI embedding model name
   - **Top K**: Retrieval top_k parameter
   - **Rerank K**: Reranking top_k parameter
   - **Qdrant Collection**: Collection name being queried
   - **Citations**: Whether citations are enabled or disabled
   - **Judge Provider**: LLM judge provider (GROQ/OpenAI)
   - **Judge Model**: LLM judge model name
4. Use **plain text (.txt) format** with simple key-value pairs
5. If evaluation is **resumed from checkpoint**, **overwrite** the existing `run_info.txt` with current config
6. File should be **mode-specific** (only capture config for the mode being evaluated)
7. File should be **config-only** (no runtime execution metadata like duration, pass rates, etc.)

## User Flow

1. User runs evaluation: `python -m evaluation.run_evaluation --mode hybrid`
2. System creates `results/hybrid/run_info.txt` immediately at start
3. System writes critical config parameters to file
4. Evaluation proceeds normally
5. User can view `run_info.txt` to see exact config used for that run

**Resume scenario**:
1. User resumes: `python -m evaluation.run_evaluation --mode hybrid --resume`
2. System **overwrites** `results/hybrid/run_info.txt` with current config
3. Resume continues from checkpoint

## Acceptance Criteria

- [ ] `run_info.txt` file is created in `results/<mode>/` directory at evaluation start
- [ ] File contains all critical parameters listed in functional requirements
- [ ] File uses plain text format with human-readable key-value pairs
- [ ] File is mode-specific (only captures config for the specific mode)
- [ ] File is overwritten (not appended) when evaluation is resumed
- [ ] File creation happens before first question is evaluated
- [ ] File does NOT include runtime execution metadata (duration, pass rates, etc.)
- [ ] File does NOT include Q&A dataset information (which files, total questions, etc.)

## User Experience

- **Interface**: CLI (evaluation script)
- **Key Interactions**:
  - User runs evaluation
  - System automatically creates `run_info.txt`
  - User can `cat results/<mode>/run_info.txt` to view config
- **Feedback**: No explicit feedback needed (silent file creation)

## Technical Requirements

- **Integration**:
  - Read config from `chatbot/config.py`, `evaluation/config.py`, `LOAD_DB/config.py`
  - Write file to `results/<mode>/run_info.txt`
  - Execute at start of `batch_evaluator.py` or `run_evaluation.py`
- **Performance**: Minimal (simple file write operation)
- **Security**: No security concerns (read-only config file)
- **Platform**: Cross-platform (simple text file)

## Data Model

**File format example** (`results/hybrid/run_info.txt`):

```
=================================================================
EVALUATION RUN CONFIGURATION
=================================================================

Mode: hybrid
Timestamp: 2025-11-25T10:30:45

-----------------------------------------------------------------
RETRIEVAL CONFIGURATION
-----------------------------------------------------------------
Qdrant Collection: tro-child-3-contextual
Embedding Model: text-embedding-3-small
Retrieval Top K: 20
Rerank Top K: 7

-----------------------------------------------------------------
LLM MODELS
-----------------------------------------------------------------
Generator Provider: groq
Generator Model: openai/gpt-oss-20b
Reranker Provider: groq
Reranker Model: openai/gpt-oss-20b
Intent Classifier Provider: groq
Intent Classifier Model: openai/gpt-oss-20b

-----------------------------------------------------------------
EVALUATION SETTINGS
-----------------------------------------------------------------
Judge Provider: groq
Judge Model: llama-3.3-70b-versatile
Citations Enabled: True

=================================================================
```

- **Storage**: Plain text file in `results/<mode>/` directory
- **Retention**: Persists until manually deleted or directory is cleared
- **Privacy**: No sensitive data (configuration only)

## Edge Cases & Error Handling

1. **Results directory doesn't exist** → Create `results/<mode>/` directory before writing file
2. **File write fails** → Log error but don't stop evaluation (non-critical)
3. **Resume with --collection override** → File shows new collection name (overwrite captures current config)
4. **Parallel evaluations** → Each mode has independent `run_info.txt` (no conflicts)

## Dependencies

- **Requires**:
  - Access to config values from `chatbot/config.py`, `evaluation/config.py`, `LOAD_DB/config.py`
  - Write permissions to `results/<mode>/` directory
- **Blocks**: None (independent feature)

## Out of Scope

- Runtime execution metadata (duration, pass rates, timestamps for completion)
- Q&A dataset information (which files evaluated, total questions)
- Detailed API endpoints or timeout values
- Automatic comparison between run_info files from different runs
- Version control integration for run_info files
- Appending/versioning of run_info files (always overwrite)

## Success Metrics

- `run_info.txt` exists in `results/<mode>/` after evaluation starts
- File contains all critical parameters with correct values
- File is human-readable and provides clear configuration snapshot
- Developers can reproduce evaluation runs using info from file

## Notes

- File is created at **start** of evaluation, not end
- File only captures **config**, not execution results
- File is **mode-specific** (each mode has its own)
- File is **overwritten** on resume (no append/version history)
- Plain text format chosen for simplicity and universal readability
