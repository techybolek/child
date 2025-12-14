# Table Parsing Non-Determinism Issue

**Status**: 🔴 Critical - Active Bug
**Discovered**: 2025-11-19
**Impact**: Non-reproducible evaluation results (47.9 vs 100/100)
**Affected Component**: Docling table extraction → Qdrant chunks → LLM generation

---

## Executive Summary

A critical bug in Docling's table parsing creates **non-deterministic evaluation failures**. The same question produces scores ranging from **47.9/100 (FAIL)** to **100/100 (PASS)** across repeated runs, making the evaluation system unreliable for table-heavy content.

**Root Cause**: Docling misaligns the last row of a table in the 89th-legislature PDF, creating corrupted markdown that the LLM generator sometimes misinterprets.

**Failure Rate**: ~50% (1 of 3 test runs failed)

---

## Problem Details

### Affected Question
- **File**: `QUESTIONS/pdfs/evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc-qa.md`
- **Question #**: 2
- **Question**: "How effective is subsidized child care in helping TANF parents find and maintain employment?"
- **Expected Answer**: "In 2022, approximately 88 percent of parents receiving TANF found employment within 12 months... 58.81% of TANF parents maintaining employment one year after entering child care in 2022."

### Corrupted Chunk
- **Source PDF**: `evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf`
- **Page**: 6 (0-indexed page 5)
- **Chunk ID**: Chunk 4 in retrieval results
- **Table**: Table 1 - "Parents Receiving TANF and Child Care"

---

## The Data Corruption

### How It Should Appear

```markdown
| Year | Percentage Finding Employment in the Year | Percentage Maintaining Employment After One Year |
|------|-------------------------------------------|--------------------------------------------------|
| 2018 | 86.06%                                    | 65.23%                                           |
| 2019 | 83.17%                                    | 59.11%                                           |
| 2020 | 76.28%                                    | 55.24%                                           |
| 2021 | 79.11%                                    | 70.41%                                           |
| 2022 | 88.45%                                    | 58.81%                                           |
```

### How Docling Parses It (Corrupted)

```markdown
| Year   | Percentage Finding Employment in the Year | Percentage Maintaining Employment After One Year |
|--------|-------------------------------------------|--------------------------------------------------|
| 2018   | 86.06%                                    | 65.23%                                           |
| 2019   | 83.17%                                    | 59.11%                                           |
| 2020   | 76.28%                                    | 55.24%                                           |
| 2021   | 79.11%                                    | 70.41%                                           |
| 58.81% | 2022                                      | 88.45%                                           | ← SCRAMBLED!
```

**Last row alignment issue**:
- **Year column**: `58.81%` (should be `2022`)
- **Finding column**: `2022` (should be `88.45%`)
- **Maintaining column**: `88.45%` (should be `58.81%`)

The values are **rotated left by one column**, causing catastrophic data corruption.

---

## Impact on LLM Generation

### Run 1 (User) - FAILED ❌

**Chatbot Answer**:
```markdown
| Year | % who found employment | % who maintained employment |
|------|------------------------|----------------------------|
| 2022 | ≈ 88 %                | 88.45 %                    | ← WRONG!
```

**What Happened**: The LLM generator looked at the corrupted Chunk 4, saw "88.45%" in the "Maintaining" column position, and reported it as the maintenance rate.

**Judge Score**: 47.9/100
- Factual Accuracy: 1.0/5 (catastrophic error)
- Completeness: 4.0/5
- Citation Quality: 3.0/5
- Coherence: 3.0/3

**Judge Reasoning**: "The answer correctly reports the 2022 employment finding rate but incorrectly states the maintenance rate, overstates it, and cites sources that may not support the figures."

### Run 2 (Claude) - PASSED ✅

**Chatbot Answer**:
```markdown
| Year | % who find employment | % who maintain employment |
|------|----------------------|---------------------------|
| 2022 | 88.45%              | 58.81%                    | ← CORRECT!
```

**What Happened**: The LLM generator somehow correctly inferred the proper alignment despite the corrupted data.

**Judge Score**: 100/100

### Run 3 (Claude) - PASSED ✅

Same as Run 2 - correctly interpreted corrupted data.

**Judge Score**: 100/100

---

## Why Non-Determinism?

The LLM generator (GROQ `openai/gpt-oss-20b`) exhibits **stochastic behavior** when interpreting ambiguous/corrupted data:

1. **Scenario A (Failure)**: LLM trusts the table structure → reads 88.45% from column 3 → reports as "maintain" percentage → **WRONG**
2. **Scenario B (Success)**: LLM recognizes structural inconsistency → infers correct alignment from context/semantics → **CORRECT**

Since LLMs have inherent non-determinism (temperature, sampling), the same corrupted input produces different interpretations across runs.

**Estimated Failure Rate**: ~33% (1 of 3 runs failed in testing)

---

## Retrieval & Reranking Behavior

### Retrieval (Consistent)
All runs retrieved the same 30 chunks, with Chunk 4 (corrupted table) appearing in top results:
- **Chunk 0**: Summary with correct 2022 figures (retrieval score: 0.707)
- **Chunk 4**: Corrupted table (retrieval score: 0.683)
- Both chunks consistently retrieved across runs ✓

### Reranking (Variable)
LLM reranker scores fluctuated slightly but Chunk 4 always passed (score ≥8):
- Run 1: Chunk 4 scored 9/10 ✓
- Run 2: Chunk 4 scored 9/10 ✓
- Run 3: Chunk 4 scored 9/10 ✓

### Generation (Non-Deterministic)
Different runs produced different answers:
- **Run 1**: Wrong interpretation → 88.45% maintain → **FAILED**
- **Run 2**: Correct interpretation → 58.81% maintain → **PASSED**
- **Run 3**: Correct interpretation → 58.81% maintain → **PASSED**

---

## Technical Analysis

### Docling Parsing Bug

The table parsing error occurs during Docling's conversion from PDF → structured document:

```python
# LOAD_DB/load_pdf_qdrant.py (simplified)
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(pdf_path)
doc = result.document

# Docling extracts table as:
table_item.export_to_dataframe(doc)
# → DataFrame with misaligned last row
```

**Hypothesis**: Docling's table detection algorithm misidentifies cell boundaries in the last row, possibly due to:
- PDF rendering artifacts
- Font/spacing variations in the 2022 row
- Table layout quirks in this specific PDF

### Where Corruption Persists

1. **PDF Extraction** (Docling) → Misaligned DataFrame
2. **Markdown Conversion** → Corrupted markdown stored in Qdrant
3. **Chunk Storage** → Chunk 4 contains corrupted table
4. **LLM Generation** → Interprets corrupted data with non-deterministic results

---

## Reproduction Steps

### Reproduce the Failure

```bash
# Run investigation multiple times
for i in {1..5}; do
  echo "=== Run $i ==="
  python -m evaluation.run_evaluation --investigate
  cat results/debug_eval.txt | grep "Composite Score"
  sleep 2
done
```

Expected output:
```
=== Run 1 ===
Composite Score: 47.9/100

=== Run 2 ===
Composite Score: 100.0/100

=== Run 3 ===
Composite Score: 100.0/100

=== Run 4 ===
Composite Score: 47.9/100

=== Run 5 ===
Composite Score: 100.0/100
```

### Inspect Corrupted Chunk

```bash
# Use qdrant-chunk-retriever skill to inspect Chunk 4
# Look for the misaligned table row where:
# - Year column contains "58.81%"
# - Finding column contains "2022"
# - Maintaining column contains "88.45%"
```

---

## Recommended Solutions

### 1. **Post-Processing Table Validation** (Short-term fix)

Add validation logic in `LOAD_DB/load_pdf_qdrant.py` to detect and correct misaligned rows:

```python
def validate_table_alignment(table_markdown: str) -> str:
    """
    Detect and fix common table misalignment patterns.

    Pattern: Last row has percentage in Year column
    Fix: Rotate values right by one column
    """
    lines = table_markdown.split('\n')

    # Check if last data row starts with a percentage
    if lines and '%' in lines[-1].split('|')[1]:
        # Parse row
        cells = [c.strip() for c in lines[-1].split('|') if c.strip()]

        # If first cell is percentage, rotate right
        if cells[0].endswith('%'):
            corrected_cells = [cells[-1]] + cells[:-1]
            lines[-1] = '| ' + ' | '.join(corrected_cells) + ' |'

    return '\n'.join(lines)
```

### 2. **Manual Chunk Correction** (Immediate workaround)

Manually correct Chunk 4 in the database:

```python
# Fix script
from qdrant_client import QdrantClient

client = QdrantClient(url=QDRANT_API_URL, api_key=QDRANT_API_KEY)

# Search for corrupted chunk
results = client.scroll(
    collection_name="tro-child-3-contextual",
    scroll_filter={
        "must": [
            {"key": "source_url", "match": {"value": "evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf"}},
            {"key": "page", "match": {"value": 6}}
        ]
    }
)

# Update with corrected markdown
for point in results:
    if "58.81% | 2022" in point.payload['text']:
        corrected_text = point.payload['text'].replace(
            "| 58.81% | 2022                                        | 88.45%                                             |",
            "| 2022   | 88.45%                                      | 58.81%                                             |"
        )
        client.update_payload(
            collection_name="tro-child-3-contextual",
            payload={"text": corrected_text},
            points=[point.id]
        )
```

### 3. **Upgrade Docling** (Medium-term)

Check for Docling updates that fix table parsing:

```bash
pip install --upgrade docling
# Test if bug persists after upgrade
```

### 4. **Surgical PDF Reload** (Recommended)

Use the surgical reload script to re-process the problematic PDF:

```bash
cd UTIL
python reload_single_pdf.py evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf
```

**Note**: This only helps if Docling is upgraded first, otherwise the corruption will persist.

### 5. **Alternative Table Parser** (Long-term)

Consider using a different table extraction library for problematic PDFs:
- **PyMuPDF4LLM** (with table detection)
- **Camelot** (table extraction specialist)
- **Tabula** (for tabular data)

---

## Monitoring & Detection

### Add Table Structure Validation

In `LOAD_DB/load_pdf_qdrant.py`, add validation:

```python
def detect_table_corruption(chunk_text: str) -> bool:
    """
    Detect common table corruption patterns.

    Returns True if chunk likely contains corrupted table.
    """
    # Check for percentage in first column
    lines = chunk_text.split('\n')
    for line in lines:
        if line.startswith('|'):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells and cells[0].endswith('%') and cells[0] != 'Year':
                return True
    return False

# During chunking
if detect_table_corruption(chunk.page_content):
    logger.warning(f"Potential table corruption detected in {source_doc}:{page_num}")
```

### Evaluation System Alerts

In `evaluation/run_evaluation.py`, add variance checking:

```python
def check_reproducibility(question_id: str, num_runs: int = 3) -> dict:
    """
    Run same question multiple times to check for non-determinism.
    """
    scores = []
    for _ in range(num_runs):
        result = chatbot.query(question)
        score = judge.evaluate(result)
        scores.append(score)

    variance = max(scores) - min(scores)
    if variance > 20:  # More than 20-point spread
        logger.warning(f"High variance detected for {question_id}: {scores}")

    return {"scores": scores, "variance": variance}
```

---

## Related Issues

- **SPECS/table_extraction_issues.md** - General table extraction problems
- **SPECS/item_level_chunking_implementation.md** - How tables are chunked
- **SPECS/evaluation_system.md** - Evaluation system overview

---

## Action Items

- [ ] Implement post-processing table validation in loading pipeline
- [ ] Manually correct Chunk 4 in Qdrant collection
- [ ] Test Docling upgrade for fix
- [ ] Add table structure validation to loading logs
- [ ] Add reproducibility checks to evaluation system
- [ ] Document all PDFs with table parsing issues
- [ ] Consider alternative table parsers for problematic PDFs

---

## Appendix: Full Debug Report Excerpts

### Failing Run (47.9/100)

```
Composite Score: 47.9/100

Individual Scores:
  Factual Accuracy:    1.0/5
  Completeness:        4.0/5
  Citation Quality:    3.0/5
  Coherence:           3.0/3

Judge Reasoning:
The answer correctly reports the 2022 employment finding rate but incorrectly
states the maintenance rate, overstates it, and cites sources that may not
support the figures.

Chatbot Answer Excerpt:
| 2022 | ≈ 88 % | 88.45 % |  ← WRONG! Should be 58.81%
```

### Passing Run (100/100)

```
Composite Score: 100.0/100

Individual Scores:
  Factual Accuracy:    5.0/5
  Completeness:        5.0/5
  Citation Quality:    5.0/5
  Coherence:           3.0/3

Judge Reasoning:
The chatbot accurately reports the 2022 employment and retention percentages,
adds useful context, cites sources, and presents the information in a clear,
structured format.

Chatbot Answer Excerpt:
| 2022 | 88.45 % | 58.81 % |  ← CORRECT!
```
