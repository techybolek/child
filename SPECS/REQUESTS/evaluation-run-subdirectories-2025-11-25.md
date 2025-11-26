# Feature Request: Organize Evaluation Results by Run

**Date:** 2025-11-25
**Status:** Refined

## Overview
Reorganize evaluation results directory structure to create a separate subdirectory for each evaluation run, while maintaining mode-level checkpoints and debug files.

## Problem Statement
Currently, all evaluation results for a given mode are stored in a flat directory structure (`results/hybrid/`, `results/dense/`, etc.) with timestamp suffixes on filenames. This makes it difficult to:
- Compare results across different runs
- Track which files belong to which evaluation run
- Understand the history of evaluation attempts
- Organize results from different experiments or configuration changes

## Users & Stakeholders
- Primary Users: Developers running evaluations, ML engineers tuning the RAG system
- Permissions: None (local filesystem)

## Functional Requirements

1. Each evaluation run creates a timestamped subdirectory within the mode directory
2. All result files for that run are stored in the run subdirectory
3. Checkpoint files remain at the mode level (not inside run directories)
4. Debug files remain at the mode level (overwritten each run)
5. Resume functionality continues the most recent run for the specified mode
6. No automatic deletion of historical runs

## Current vs. Proposed Structure

### Current Structure
```
results/
├── hybrid/
│   ├── checkpoint.json
│   ├── debug_eval.txt
│   ├── detailed_results_20251125_143022.jsonl
│   ├── evaluation_summary_20251125_143022.json
│   ├── evaluation_report_20251125_143022.txt
│   ├── failure_analysis_20251125_143022.txt
│   ├── detailed_results_20251125_150045.jsonl
│   ├── evaluation_summary_20251125_150045.json
│   └── ... (mixed files from multiple runs)
├── dense/
└── openai/
```

### Proposed Structure
```
results/
├── hybrid/
│   ├── checkpoint.json              # Mode-level checkpoint
│   ├── debug_eval.txt               # Mode-level debug (overwritten)
│   ├── RUN_20251125_143022/
│   │   ├── detailed_results.jsonl
│   │   ├── evaluation_summary.json
│   │   ├── evaluation_report.txt
│   │   └── failure_analysis.txt     # Only if failures exist
│   └── RUN_20251125_150045/
│       ├── detailed_results.jsonl
│       ├── evaluation_summary.json
│       └── evaluation_report.txt
├── dense/
│   ├── checkpoint.json
│   ├── debug_eval.txt
│   └── RUN_20251125_151230/
│       └── ... (same file structure)
└── openai/
    └── ... (same pattern)
```

## User Flow

### New Evaluation Run
1. User runs: `python -m evaluation.run_evaluation --mode hybrid`
2. System creates: `results/hybrid/RUN_<timestamp>/`
3. System writes results to the new run directory
4. System updates mode-level `checkpoint.json`
5. System overwrites mode-level `debug_eval.txt` if `--debug` flag used

### Resume Existing Run
1. User runs: `python -m evaluation.run_evaluation --mode hybrid --resume`
2. System reads mode-level `checkpoint.json`
3. System identifies most recent run directory (latest timestamp)
4. System appends new results to files in that run directory
5. System updates mode-level `checkpoint.json` as it progresses

## Acceptance Criteria

- [ ] New evaluation runs create `RUN_YYYYMMDD_HHMMSS/` subdirectory in mode directory
- [ ] Timestamp format: `YYYYMMDD_HHMMSS` (e.g., `20251125_143022`)
- [ ] All result files inside run directory have clean names (no timestamp suffix)
- [ ] Result files: `detailed_results.jsonl`, `evaluation_summary.json`, `evaluation_report.txt`
- [ ] Optional file: `failure_analysis.txt` (only created if failures exist)
- [ ] Checkpoint file stays at mode level: `results/<mode>/checkpoint.json`
- [ ] Debug file stays at mode level: `results/<mode>/debug_eval.txt`
- [ ] `--resume` flag identifies and continues most recent run for the specified mode
- [ ] Resumed runs append to existing files in the most recent run directory
- [ ] No automatic deletion of old run directories
- [ ] Works correctly for all three modes: `hybrid`, `dense`, `openai`
- [ ] Parallel evaluation (multiple modes simultaneously) still works without conflicts

## User Experience

### Interface
- CLI (`evaluation/run_evaluation.py`)

### Key Interactions
```bash
# Start new evaluation run
python -m evaluation.run_evaluation --mode hybrid
# Output: "Created run directory: results/hybrid/RUN_20251125_143022/"

# Resume most recent run
python -m evaluation.run_evaluation --mode hybrid --resume
# Output: "Resuming run: results/hybrid/RUN_20251125_143022/"

# List runs for a mode (future enhancement, not required)
# ls results/hybrid/
# Output: RUN_20251125_143022/  RUN_20251125_150045/
```

### Feedback Messages
- **New run created**: "Created run directory: results/{mode}/RUN_{timestamp}/"
- **Resuming run**: "Resuming run: results/{mode}/RUN_{timestamp}/"
- **Run completed**: "Results saved to: results/{mode}/RUN_{timestamp}/"

## Technical Requirements

### Integration
- Modify `evaluation/batch_evaluator.py` to create/detect run directories
- Modify `evaluation/reporter.py` to write to run directories
- Modify `evaluation/config.py` to add run directory path helpers

### Performance
- No performance impact (just directory reorganization)

### Security
- None (local filesystem only)

### Platform
- Desktop (Linux/macOS/Windows compatible path handling)

## Data Model

### Run Directory Naming
- **Format**: `RUN_YYYYMMDD_HHMMSS`
- **Timestamp**: Derived from `datetime.now().strftime('%Y%m%d_%H%M%S')`
- **Example**: `RUN_20251125_143022`

### File Locations
| File Type | Location | Persistence |
|-----------|----------|-------------|
| Detailed results | `results/<mode>/RUN_<timestamp>/detailed_results.jsonl` | Per run |
| Summary JSON | `results/<mode>/RUN_<timestamp>/evaluation_summary.json` | Per run |
| Report TXT | `results/<mode>/RUN_<timestamp>/evaluation_report.txt` | Per run |
| Failure analysis | `results/<mode>/RUN_<timestamp>/failure_analysis.txt` | Per run (optional) |
| Checkpoint | `results/<mode>/checkpoint.json` | Mode-level |
| Debug output | `results/<mode>/debug_eval.txt` | Mode-level |

### Retention
- **Policy**: Never auto-delete
- **Cleanup**: Manual only (user deletes old `RUN_*/` directories)

## Edge Cases & Error Handling

1. **Multiple runs same timestamp** → Unlikely (second-level precision), but if collision: append `_1`, `_2` suffix
2. **Resume with no checkpoint** → Error message: "No checkpoint found for mode {mode}"
3. **Resume with no existing runs** → Error message: "No existing runs found for mode {mode}"
4. **Checkpoint references non-existent run** → Create new run directory
5. **Disk space full** → Propagate OS error (no special handling)
6. **Invalid run directory format** → Ignore (don't affect new runs)
7. **Partial run directory** → Resume appends/overwrites files normally

## Dependencies

### Requires
- Python `pathlib` for cross-platform path handling
- Python `datetime` for timestamp generation
- Python `glob` for finding most recent run directory

### Blocks
- None

## Out of Scope

- UI for browsing historical runs (use filesystem/CLI)
- Automatic cleanup/retention policies
- Run metadata files (e.g., config snapshots)
- Run comparison tools
- Custom run labels/names (timestamp only)
- Migration script for old results (manual if needed)

## Success Metrics

- All evaluation runs create properly named run directories
- `--resume` correctly identifies and continues most recent run
- Parallel evaluations (different modes) work without conflicts
- Historical runs are preserved and easily identifiable by timestamp
- File paths in code are cleaner (no timestamp suffix concatenation)

## Implementation Notes

### Key Code Changes
1. **`evaluation/config.py`**: Add helper functions:
   - `create_run_directory(mode: str) -> Path`
   - `get_most_recent_run(mode: str) -> Path | None`

2. **`evaluation/batch_evaluator.py`**:
   - Create run directory at start or detect on resume
   - Pass run directory to reporter

3. **`evaluation/reporter.py`**:
   - Remove timestamp suffix from filenames
   - Write files to run directory path

4. **`evaluation/run_evaluation.py`**:
   - Add user feedback for run directory creation/detection

### Backward Compatibility
- Old result files in flat structure remain accessible
- No migration required (old and new structures coexist)

## Notes

This change improves organization and makes it easier to compare results across different configurations, code changes, or experiments while maintaining the existing checkpoint and debug file behavior.
