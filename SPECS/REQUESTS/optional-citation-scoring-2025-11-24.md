# Feature Request: Optional Citation Scoring in Evaluation System

**Date:** 2025-11-24
**Status:** Refined

## Overview
Add ability to run chatbot evaluations without scoring citation quality, while still collecting and displaying sources. This allows focus on answer quality (accuracy, completeness, coherence) independent of source documentation.

## Problem Statement
Current evaluation system always scores citation quality (10% weight), which may not be relevant in all contexts:
- When comparing retrieval modes where citation handling differs significantly (e.g., OpenAI FileSearch vs custom RAG)
- When citation quality is less important than content accuracy (e.g., testing answer generation independent of retrieval)
- When evaluating non-citation-based systems or testing alternative source attribution methods

Disabling citation scoring allows fairer comparisons and more focused evaluation on core answer quality.

## Users & Stakeholders
- **Primary Users**: Developers running evaluations to test retrieval modes, prompt changes, or model performance
- **Permissions**: No special permissions required (same access as current evaluation system)

## Functional Requirements

1. **Configuration Toggle**
   - Add `DISABLE_CITATION_SCORING` boolean flag in `evaluation/config.py`
   - Default: `False` (citations enabled, current behavior)
   - No command-line override flags (config-only control)

2. **Modified Scoring Calculation**
   - When `DISABLE_CITATION_SCORING=True`:
     - Evaluate only 3 criteria: Accuracy, Completeness, Coherence
     - Normalize weights proportionally to maintain 100% total:
       - Accuracy: 50% → 55.6% (divide by 0.9)
       - Completeness: 30% → 33.3% (divide by 0.9)
       - Coherence: 10% → 11.1% (divide by 0.9)
     - Calculate composite score from 3 criteria only

3. **Source Collection Unchanged**
   - Continue retrieving and storing source citations
   - Display sources in all output formats (console, JSONL, reports)
   - Only skip the citation quality scoring step

4. **Output Metadata**
   - Mark all outputs with "citation scoring disabled" indicator:
     - JSONL: Add `"citation_scoring_enabled": false` field
     - JSON summary: Add `"citation_scoring_enabled": false` field
     - TXT report: Add header note explaining modified scoring
   - Set `citation_quality` field to `null` in detailed results JSONL
   - Omit citation quality from average scores in summary

5. **Checkpoint Compatibility**
   - Store `citation_scoring_enabled` boolean in `checkpoint.json`
   - On resume: Compare checkpoint's citation mode with current config
   - If mismatch: Block resume with clear error message explaining incompatibility
   - Error message must show checkpoint mode vs current mode and suggest fix

6. **Threshold Behavior**
   - Keep `STOP_ON_FAIL_THRESHOLD=70` unchanged
   - Same threshold applies regardless of citation scoring mode
   - No automatic threshold adjustment

## User Flow

### Initial Evaluation with Citation Scoring Disabled
1. Developer sets `DISABLE_CITATION_SCORING=True` in `evaluation/config.py`
2. Runs: `python -m evaluation.run_evaluation --mode hybrid`
3. System evaluates questions using 3 criteria (no citation scoring)
4. Sources still collected and displayed
5. Checkpoint saved with `citation_scoring_enabled: false`
6. Reports generated with "Citation scoring disabled" header note

### Resume with Mismatched Citation Mode
1. Developer completes 10 questions with `DISABLE_CITATION_SCORING=True`
2. Evaluation stops on failure (question 11)
3. Developer changes `DISABLE_CITATION_SCORING=False` in config
4. Attempts resume: `python -m evaluation.run_evaluation --mode hybrid --resume`
5. System detects mismatch, shows error:
   ```
   Error: Cannot resume - citation scoring mode mismatch
   Checkpoint mode: citation_scoring_enabled=true
   Current config: DISABLE_CITATION_SCORING=False (enabled)

   Fix: Set DISABLE_CITATION_SCORING=True to match checkpoint
   Or: Delete checkpoint to start fresh evaluation
   ```
6. Developer must fix config or delete checkpoint

## Acceptance Criteria

- [ ] `DISABLE_CITATION_SCORING` flag added to `evaluation/config.py` with default `False`
- [ ] When disabled, composite score calculated from 3 criteria with normalized weights (55.6%, 33.3%, 11.1%)
- [ ] Source citations still collected and stored in all outputs
- [ ] `citation_quality` field set to `null` in detailed results JSONL when disabled
- [ ] `citation_scoring_enabled` boolean added to:
  - Detailed results JSONL (per question)
  - Evaluation summary JSON (metadata section)
  - Checkpoint JSON
- [ ] Evaluation report TXT includes header note when citation scoring disabled
- [ ] Average citation score omitted from summary statistics when disabled
- [ ] Resume blocked if checkpoint citation mode differs from current config
- [ ] Error message clearly explains mismatch and suggests fix
- [ ] Stop-on-fail threshold remains 70 regardless of citation mode
- [ ] All three evaluation modes (hybrid, dense, openai) support citation toggling

## User Experience

### Interface
**CLI** - No new flags, config-only toggle

### Key Interactions
1. **Enable/Disable**: Edit `evaluation/config.py`, set `DISABLE_CITATION_SCORING=True/False`
2. **Visual Indicators**: All outputs clearly marked with citation mode status
3. **Resume Safety**: Automatic validation prevents inconsistent scoring across questions

### Feedback Messages

**Success (Citation Scoring Disabled)**:
```
Evaluation Settings:
  Mode: hybrid
  Citation Scoring: DISABLED
  Scoring Criteria: Accuracy (55.6%), Completeness (33.3%), Coherence (11.1%)
```

**Error (Resume Mismatch)**:
```
❌ Error: Cannot resume - citation scoring mode mismatch
   Checkpoint: citation_scoring_enabled=false
   Current:    DISABLE_CITATION_SCORING=True (disabled)

   To fix:
   - Set DISABLE_CITATION_SCORING=False in evaluation/config.py
   - Or delete results/<mode>/checkpoint.json to restart
```

## Technical Requirements

### Integration
- Modify `evaluation/batch_evaluator.py` to read config flag
- Update `evaluation/judge.py` to skip citation scoring when disabled
- Modify `evaluation/reporter.py` to add metadata and handle null citations
- Update `evaluation/run_evaluation.py` to validate checkpoint compatibility

### Performance
- No performance impact (skipping citation scoring may marginally speed up evaluation)

### Security
- No security implications (read-only configuration change)

### Platform
- Cross-platform (Python-based, same as existing evaluation system)

## Data Model

### Configuration Schema (`evaluation/config.py`)
```python
# Citation Scoring Toggle
DISABLE_CITATION_SCORING: bool = False  # Set True to evaluate without citation scoring
```

### Checkpoint Schema (`results/<mode>/checkpoint.json`)
```json
{
  "last_completed_index": 9,
  "last_file": "bcy-26-psoc-chart-twc-qa.md",
  "citation_scoring_enabled": false,
  "timestamp": "2025-11-24T10:30:00"
}
```

### Detailed Results Schema (`results/<mode>/detailed_results_*.jsonl`)
```json
{
  "source_file": "test-qa.md",
  "question_num": 1,
  "question": "...",
  "expected_answer": "...",
  "chatbot_answer": "...",
  "sources": [...],
  "scores": {
    "accuracy": 4,
    "completeness": 4,
    "citation_quality": null,
    "coherence": 3,
    "composite": 88.9
  },
  "citation_scoring_enabled": false
}
```

### Storage
- Configuration stored in `evaluation/config.py` (version controlled)
- Citation mode stored in checkpoint JSON (per evaluation session)
- No database changes required

### Retention
- Checkpoint deleted on successful completion or explicit restart
- Citation mode metadata persists in all output files for audit trail

## Edge Cases & Error Handling

1. **Resume with mismatched citation mode** → Block with error message explaining mismatch
2. **Checkpoint exists but missing `citation_scoring_enabled` field** → Treat as citations enabled (backward compatibility)
3. **Config changes mid-evaluation** → Checkpoint validation catches mismatch on resume
4. **Null citation scores in reports** → Display as "N/A" or omit from averages
5. **Legacy checkpoints without citation field** → Assume `citation_scoring_enabled=true` (default behavior)

## Dependencies

### Requires
- Existing evaluation system (no external dependencies)
- `evaluation/config.py` for configuration storage
- `evaluation/batch_evaluator.py`, `evaluation/judge.py`, `evaluation/reporter.py` modifications

### Blocks
- None (non-breaking change, backward compatible)

## Out of Scope

- Command-line flags (`--no-citations`, `--citations`) - config-only by design
- Dynamic threshold adjustment based on citation mode
- Separate thresholds for different citation modes
- Automatic checkpoint migration for citation mode changes
- Force-resume flag to override citation mismatch (must edit config or delete checkpoint)
- Per-question citation toggling (all-or-nothing per evaluation run)
- UI/web interface controls (CLI evaluation tool only)

## Success Metrics

### Functional Success
- Evaluation completes successfully with citation scoring disabled
- Composite scores calculated correctly using 3-criterion formula
- Sources still visible in all outputs
- Resume blocked appropriately when citation mode differs

### Quality Metrics
- No regression in existing citation-enabled evaluations
- Clear documentation of citation mode in all outputs
- Intuitive error messages for configuration mismatches

### Performance
- No performance degradation
- Possible minor speedup from skipping citation scoring step

## Notes

### Design Rationale

**Config-only (no CLI flags)**:
- Simpler implementation (single source of truth)
- Prevents accidental inconsistency (forgetting flag on resume)
- Forces intentional decision (edit config file)
- Checkpoint validation ensures consistency

**Keep collecting sources**:
- Minimal code changes (only scoring logic affected)
- Sources still valuable for debugging/analysis
- Allows manual citation review without rerunning evaluation

**Proportional weight redistribution**:
- Mathematically sound (divide by 0.9 to maintain 100% total)
- Preserves relative importance of remaining criteria
- Avoids arbitrary new weights

**Block resume on mismatch**:
- Ensures scoring consistency across all questions
- Prevents invalid comparisons (some questions scored with citations, others without)
- Clear error message guides user to fix

### Future Enhancements (Not in Scope)
- Per-mode citation defaults (e.g., always disable for `openai` mode)
- Separate citation scoring for different source types (PDF vs webpage)
- Weighted citation scoring based on source authority
- Multi-configuration comparison reports (side-by-side citation vs no-citation)

### Implementation Priority
1. Add config flag and checkpoint field (low risk)
2. Modify scoring calculation (core logic)
3. Update output formatting (metadata, N/A handling)
4. Add checkpoint validation (safety check)
5. Update documentation and error messages
