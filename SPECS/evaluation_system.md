# Chatbot Evaluation System

LLM-as-a-Judge evaluation framework for the Texas Childcare Chatbot. Automatically tests chatbot responses against curated Q&A pairs and scores them on multiple criteria.

## Quick Start

```bash
# Run full evaluation on all Q&A files
python run_evaluation.py

# Test mode - evaluate first 5 questions
python run_evaluation.py --test --limit 5

# Evaluate specific Q&A file
python run_evaluation.py --file bcy-26-psoc-chart-twc-qa.md

# Use specific Qdrant collection
python run_evaluation.py --collection tro-child-3-contextual

# Debug failed question (after stop-on-fail)
python test_failed.py
```

## System Overview

### Architecture

```
run_evaluation.py (entry point)
    ↓
BatchEvaluator (evaluation/batch_evaluator.py)
    ↓
    ├─→ ChatbotEvaluator → RAGHandler (queries chatbot)
    ├─→ LLMJudge → GROQ/OpenAI (scores response)
    └─→ Reporter (generates 3 report types)
```

### Pipeline Flow

1. **Load Q&A Pairs**: Parse markdown files from `QUESTIONS/pdfs/`
2. **Query Chatbot**: Send question to RAGHandler
3. **Judge Response**: Score answer on 4 criteria using LLM judge
4. **Check Threshold**: Stop if score < 70 (stop-on-fail)
5. **Generate Reports**: Create JSONL, JSON, and TXT reports in `results/`

### Stop-on-Fail Behavior

When a question scores < 70:
- ❌ Evaluation stops immediately
- 📊 Detailed failure report printed to console
- 🧪 `test_failed.py` auto-generated in project root
- 💾 No checkpoint saved

**Philosophy**: Fix failures incrementally rather than batch-processing multiple failures.

## Auto-Generated test_failed.py

### When Generated

`test_failed.py` is auto-generated when evaluation stops due to a score below threshold (default: 70).

### Contents

The file contains:
- Auto-generated docstring with source, score, timestamp
- Imports for RAGHandler
- Expected answer (from Q&A file) as comment
- Failed question as variable
- Code to query RAGHandler directly
- Formatted output comparing expected vs chatbot answer

### Usage

```bash
# Run with default collection
python test_failed.py

# Run with specific collection
python test_failed.py --collection tro-child-3-contextual
```

**Key benefit**: Bypasses full evaluation pipeline for quick iteration on fixing specific failures.

### Example Output

```
QUESTION:
What income levels correspond to each SMI percentage for a family of 5?

EXPECTED ANSWER:
For a family of 5, the monthly income thresholds are: $105 (1% SMI)...

CHATBOT ANSWER:
[Current chatbot response]

SOURCES:
- bcy-26-income-eligibility-and-maximum-psoc-twc.pdf, Page 0
```

## Input Format: Q&A Markdown Files

Location: `QUESTIONS/pdfs/*.md`

### Format Structure

```markdown
# Title

## Optional Section

### Q1: Question text here?
**A1:** Expected answer text here.

### Q2: Another question?
**A2:** Another expected answer.
```

### Parsing Rules

- **Pattern**: `### Q<num>:` followed by `**A<num>:**`
- **Numbering**: Q/A numbers must match (e.g., Q5 → A5)
- **Whitespace**: Leading/trailing whitespace automatically stripped
- **Separator**: Questions separated by `\n###` or end of file

### Example

```markdown
### Q5: What income levels correspond to each SMI percentage for a family of 5?
**A5:** For a family of 5, the monthly income thresholds are: $105 (1% SMI), $1,571 (15% SMI), $2,617 (25% SMI), $3,664 (35% SMI), $4,711 (45% SMI), $5,757 (55% SMI), $6,804 (65% SMI), $7,851 (75% SMI), and $8,897 (85% SMI). These thresholds determine which sliding fee scale bracket the family falls into.
```

## Output Format

### 1. Detailed Results (JSONL)

**File**: `results/detailed_results_YYYYMMDD_HHMMSS.jsonl`

One JSON object per line:
```json
{"source_file": "bcy-26-psoc-chart-twc-qa.md", "question_num": 5, "question": "...", "expected_answer": "...", "chatbot_answer": "...", "sources": [...], "response_type": "information", "response_time": 3.45, "scores": {...}}
```

### 2. Evaluation Summary (JSON)

**File**: `results/evaluation_summary_YYYYMMDD_HHMMSS.json`

```json
{
  "timestamp": "2025-11-04T07:22:28",
  "total_evaluated": 25,
  "average_scores": {
    "accuracy": 4.2,
    "completeness": 3.8,
    "citation_quality": 4.5,
    "coherence": 2.9,
    "composite": 75.3
  },
  "performance": {
    "excellent": 10,
    "good": 8,
    "needs_review": 5,
    "failed": 2,
    "pass_rate": 72.0
  },
  "response_time": {
    "average": 3.45,
    "min": 2.1,
    "max": 5.8
  }
}
```

### 3. Human-Readable Report (TXT)

**File**: `results/evaluation_report_YYYYMMDD_HHMMSS.txt`

```
================================================================================
CHATBOT EVALUATION REPORT
================================================================================

Timestamp: 2025-11-04T07:22:28
Total Evaluated: 25 Q&A pairs

================================================================================
AVERAGE SCORES
================================================================================
Composite Score:     75.3/100
Factual Accuracy:    4.20/5
Completeness:        3.80/5
Citation Quality:    4.50/5
Coherence:           2.90/3

================================================================================
PERFORMANCE BREAKDOWN
================================================================================
Excellent (≥85):       10 ( 40.0%)
Good (70-84):           8 ( 32.0%)
Needs Review (50-69):   5 ( 20.0%)
Failed (<50):           2 (  8.0%)

Overall Pass Rate:   72.0%
```

### 4. Failure Analysis (TXT)

**File**: `results/failure_analysis_YYYYMMDD_HHMMSS.txt` (only if failures exist)

Lists all questions scoring < 50 with details.

## Scoring System

### Criteria and Weights

| Criterion          | Weight | Max Points | Description                                |
|--------------------|--------|------------|--------------------------------------------|
| Factual Accuracy   | 50%    | 5          | Correctness of information                 |
| Completeness       | 30%    | 5          | Coverage of expected answer                |
| Citation Quality   | 10%    | 5          | Source documentation                       |
| Coherence          | 10%    | 3          | Clarity and readability                    |

### Composite Score Calculation

```python
composite = (accuracy * 10 * 0.5) +
            (completeness * 10 * 0.3) +
            (citation_quality * 10 * 0.1) +
            (coherence * 10/3 * 0.1)
```

Result: 0-100 scale

### Performance Thresholds

- **Excellent**: ≥ 85
- **Good**: 70-84 (pass)
- **Needs Review**: 50-69
- **Failed**: < 50
- **Stop-on-Fail**: < 70 (default)

## Command Reference

### Basic Usage

```bash
# Evaluate all Q&A pairs
python run_evaluation.py

# Limit to first N questions
python run_evaluation.py --limit 10

# Test mode (quick check)
python run_evaluation.py --test --limit 5
```

### Single File Evaluation

```bash
# Evaluate specific Q&A file
python run_evaluation.py --file bcy-26-psoc-chart-twc-qa.md
```

### Collection Override

```bash
# Use non-default Qdrant collection
python run_evaluation.py --collection tro-child-3-contextual
```

### Debug Failed Question

```bash
# Run auto-generated test
python test_failed.py

# With specific collection
python test_failed.py --collection tro-child-1
```

## Configuration

Configuration file: `evaluation/config.py`

### Judge Settings

```python
JUDGE_PROVIDER = 'groq'              # or 'openai'
JUDGE_MODEL = 'llama-3.3-70b-versatile'
JUDGE_API_KEY = os.getenv('GROQ_API_KEY')
```

### Processing Settings

```python
PARALLEL_WORKERS = 5                 # Concurrent evaluations
TIMEOUT = 30                         # Seconds per evaluation
CHECKPOINT_INTERVAL = 50             # Save checkpoint every N questions
```

### Paths

```python
QA_DIR = 'QUESTIONS/pdfs'            # Q&A markdown files
RESULTS_DIR = 'results'              # Output location
```

### Scoring

```python
WEIGHTS = {
    'accuracy': 0.5,                 # 50%
    'completeness': 0.3,             # 30%
    'citation_quality': 0.1,         # 10%
    'coherence': 0.1                 # 10%
}

THRESHOLDS = {
    'excellent': 85,
    'good': 70,
    'needs_review': 50
}

STOP_ON_FAIL_THRESHOLD = 70          # Stop evaluation if score < 70
```

## Typical Workflow

1. **Create Q&A file**: Add questions to `QUESTIONS/pdfs/your-file-qa.md`
2. **Run test evaluation**: `python run_evaluation.py --test --limit 5`
3. **Fix failures**: Use `test_failed.py` for quick iteration
4. **Run full evaluation**: `python run_evaluation.py`
5. **Review reports**: Check `results/` directory

## Key Files

- `run_evaluation.py` - Main entry point
- `evaluation/batch_evaluator.py` - Core evaluation logic
- `evaluation/evaluator.py` - Chatbot query wrapper
- `evaluation/judge.py` - LLM-based scoring
- `evaluation/reporter.py` - Report generation
- `evaluation/qa_parser.py` - Q&A file parsing
- `evaluation/config.py` - Configuration
- `test_failed.py` - Auto-generated debug script (appears after stop-on-fail)
