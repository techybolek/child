# Chatbot Evaluation System

LLM-as-a-Judge evaluation framework for the Texas Childcare Chatbot. Tests chatbot responses against curated Q&A pairs with scoring on multiple criteria.

## Quick Start

```bash
# Run evaluation with specific mode
python -m evaluation.run_evaluation --mode hybrid
python -m evaluation.run_evaluation --mode dense
python -m evaluation.run_evaluation --mode openai
python -m evaluation.run_evaluation --mode kendra

# Test mode (limit questions)
python -m evaluation.run_evaluation --mode hybrid --test --limit 5

# Resume from checkpoint after failure
python -m evaluation.run_evaluation --mode hybrid --resume --resume-limit 1
```

## Architecture

```
evaluation/run_evaluation.py (entry point)
    ↓
BatchEvaluator (batch_evaluator.py)
    ↓
    ├── ChatbotEvaluator / OpenAIEvaluator / KendraEvaluator
    ├── LLMJudge (scores response)
    └── Reporter (generates reports)
```

## Pipeline Flow

1. **Load Q&A Pairs** - Parse markdown files from `QUESTIONS/pdfs/`
2. **Query Chatbot** - Send question to appropriate evaluator
3. **Judge Response** - Score on 4 criteria using LLM judge
4. **Check Threshold** - Stop if score < 70 (stop-on-fail)
5. **Generate Reports** - Create JSONL, JSON, TXT in `results/<mode>/RUN_<timestamp>/`

## Evaluation Modes

| Mode | Evaluator | Description |
|------|-----------|-------------|
| `hybrid` | ChatbotEvaluator | Dense + sparse with RRF fusion |
| `dense` | ChatbotEvaluator | Dense-only semantic search |
| `openai` | OpenAIEvaluator | GPT model with FileSearch tool |
| `kendra` | KendraEvaluator | Amazon Kendra retrieval |

### Running Parallel Evaluations

Each mode writes to isolated directories, allowing simultaneous execution:

```bash
# Terminal 1
python -m evaluation.run_evaluation --mode hybrid

# Terminal 2
python -m evaluation.run_evaluation --mode dense

# Terminal 3
python -m evaluation.run_evaluation --mode kendra
```

## Output Structure

```
results/
├── hybrid/
│   └── RUN_20251127_143022/
│       ├── checkpoint.json           # Resume checkpoint
│       ├── run_info.json             # Run metadata
│       ├── detailed_results_*.jsonl  # Per-question results
│       ├── evaluation_summary_*.json # Aggregate statistics
│       └── evaluation_report_*.txt   # Human-readable report
├── dense/
│   └── RUN_*/
├── openai/
│   └── RUN_*/
└── kendra/
    └── RUN_*/
```

## Command Reference

### Basic Usage

```bash
python -m evaluation.run_evaluation --mode hybrid         # Full evaluation
python -m evaluation.run_evaluation --mode hybrid --limit 10  # Limit questions
python -m evaluation.run_evaluation --mode hybrid --test      # Quick test
```

### File Selection

```bash
python -m evaluation.run_evaluation --mode hybrid --file bcy-26-psoc-chart-twc-qa.md
```

### Resume After Failure

```bash
python -m evaluation.run_evaluation --mode hybrid --resume              # Continue from checkpoint
python -m evaluation.run_evaluation --mode hybrid --resume --resume-limit 1  # Re-evaluate just failed question
python -m evaluation.run_evaluation --mode hybrid --resume --debug      # With debug output
```

### Advanced Options

```bash
python -m evaluation.run_evaluation --mode hybrid --run-name experiment1  # Custom run name
python -m evaluation.run_evaluation --mode hybrid --no-stop-on-fail      # Don't stop on low scores
python -m evaluation.run_evaluation --mode hybrid --clear-checkpoint     # Delete checkpoint after success
python -m evaluation.run_evaluation --mode hybrid --capture-on-error     # Save failed questions
python -m evaluation.run_evaluation --mode hybrid --debug                # Show retrieval details
python -m evaluation.run_evaluation --mode hybrid --investigate          # Re-evaluate same question
python -m evaluation.run_evaluation --mode hybrid --retrieval-top-k 50   # Override retrieval limit
```

### All CLI Arguments

| Argument | Description |
|----------|-------------|
| `--mode` | Evaluation mode: hybrid, dense, openai, kendra |
| `--test` | Test mode flag |
| `--limit N` | Limit to N questions |
| `--file FILENAME` | Evaluate specific Q&A file |
| `--resume` | Resume from checkpoint |
| `--resume-limit N` | Process only N questions after resume |
| `--debug` | Show retrieval details |
| `--investigate` | Re-evaluate same question (debug) |
| `--retrieval-top-k N` | Override retrieval limit |
| `--run-name PREFIX` | Custom run directory prefix |
| `--clear-checkpoint` | Delete checkpoint after successful run |
| `--capture-on-error` | Save failed question details |
| `--no-stop-on-fail` | Continue evaluation on low scores |

## Scoring System

### Criteria and Weights

| Criterion | Weight | Max | Description |
|-----------|--------|-----|-------------|
| Factual Accuracy | 50% | 5 | Correctness of information |
| Completeness | 30% | 5 | Coverage of expected answer |
| Citation Quality | 10% | 5 | Source documentation (disabled by default) |
| Coherence | 10% | 3 | Clarity and readability |

### Composite Score Calculation

```python
composite = (accuracy * 10 * 0.5) +
            (completeness * 10 * 0.3) +
            (citation_quality * 10 * 0.1) +
            (coherence * 10/3 * 0.1)
```

**Result:** 0-100 scale

### When Citation Scoring Disabled

Current default: `DISABLE_CITATION_SCORING = True`

Weights redistribute to:
- Accuracy: 55.6%
- Completeness: 33.3%
- Coherence: 11.1%

### Performance Thresholds

| Category | Score Range |
|----------|-------------|
| Excellent | >= 85 |
| Good | 70-84 (pass) |
| Needs Review | 50-69 |
| Failed | < 50 |

**Stop-on-Fail Threshold:** < 70

## Resume System

### How It Works

When evaluation stops on failure:
1. **Checkpoint Saved** - Progress up to (but not including) failed question
2. **Resume Available** - Use `--resume` to continue
3. **Failed Question Re-evaluated** - Not included in checkpoint

### Typical Fix-and-Resume Workflow

1. Evaluation stops on Q15 (score < 70)
2. Checkpoint saved with Q1-Q14 complete
3. Investigate failure in console output
4. Fix issue (update chunking, prompts, etc.)
5. Re-evaluate: `--resume --resume-limit 1` to test Q15 only
6. Continue: `--resume` for remaining questions

## Input Format

**Location:** `QUESTIONS/pdfs/*.md`

### Q&A Format

```markdown
### Q1: Question text here?
**A1:** Expected answer text here.

### Q2: Another question?
**A2:** Another expected answer.
```

### Parsing Rules

- Pattern: `### Q<num>:` followed by `**A<num>:**`
- Q/A numbers must match
- Whitespace automatically stripped

## Configuration

**File:** `evaluation/config.py`

### Judge Settings

```python
JUDGE_PROVIDER = 'groq'
JUDGE_MODEL = 'openai/gpt-oss-20b'
```

### Processing

```python
PARALLEL_WORKERS = 5
TIMEOUT = 30  # seconds
CHECKPOINT_INTERVAL = 50
```

### Scoring

```python
WEIGHTS = {
    'accuracy': 0.5,
    'completeness': 0.3,
    'citation_quality': 0.1,
    'coherence': 0.1
}

THRESHOLDS = {
    'excellent': 85,
    'good': 70,
    'needs_review': 50
}

STOP_ON_FAIL_THRESHOLD = 70
DISABLE_CITATION_SCORING = True
```

### Paths

```python
QA_DIR = 'QUESTIONS/pdfs'
RESULTS_DIR = 'results'
VALID_MODES = ['hybrid', 'dense', 'openai', 'kendra']
```

## Key Files

| File | Purpose |
|------|---------|
| `run_evaluation.py` | Main entry point |
| `batch_evaluator.py` | Core evaluation loop |
| `evaluator.py` | ChatbotEvaluator (hybrid/dense) |
| `openai_evaluator.py` | OpenAI agent evaluator |
| `kendra_evaluator.py` | Amazon Kendra evaluator |
| `judge.py` | LLM-as-a-Judge scoring |
| `reporter.py` | Report generation |
| `qa_parser.py` | Q&A file parsing |
| `run_info_writer.py` | Run metadata tracking |
| `config.py` | Configuration |

## Typical Workflow

1. **Create Q&A file** - Add to `QUESTIONS/pdfs/your-file-qa.md`
2. **Test evaluation** - `python -m evaluation.run_evaluation --mode hybrid --test --limit 5`
3. **Fix failures** - Use `--resume --resume-limit 1`
4. **Full evaluation** - `python -m evaluation.run_evaluation --mode hybrid`
5. **Review reports** - Check `results/hybrid/RUN_*/`

## Troubleshooting

### Checkpoint not found
Each mode has its own checkpoint in `results/<mode>/checkpoint.json`. Ensure you specify the correct `--mode`.

### Score always low
Check judge model configuration. Verify Q&A file format matches expected pattern.

### Kendra mode fails
Ensure AWS credentials are configured and `KENDRA_INDEX_ID` is set in config.
