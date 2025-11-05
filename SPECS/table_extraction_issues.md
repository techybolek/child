# PDF Table Extraction Issues - Investigation Report

**Date:** 2025-11-04
**Issue:** Chatbot returns incorrect weekly PSoC amount ($103 instead of $43)
**Test Case:** Family of 3 with two children in care at 45% SMI
**Status:** Root cause identified, solutions proposed

---

## Executive Summary

The chatbot failed an evaluation test by returning an incorrect weekly Parent Share of Cost (PSoC) amount. When asked "How much does a family of 3 with two children in care pay at 45% SMI?", the chatbot correctly returned $191/month but incorrectly returned $103/week instead of the correct $43/week.

**Root Cause:** The LLM is reading the wrong column position in the PSoC sliding fee scale table. The $103 value corresponds to the 85% SMI column (rightmost column), not the 45% SMI column (middle column).

**Impact:** High - This is a critical accuracy issue for a financial assistance application. Users relying on this information would receive incorrect cost estimates.

**Quick Fix:** Enhance the response generation prompt with table-reading instructions and add income cross-referencing guidance.

---

## Test Case Details

### Failed Question
```
How much does a family of 3 with two children in care pay at 45% SMI?
```

### Expected Answer
```
A family of 3 at 45% SMI has a monthly income of $3,411.
Their monthly PSoC for two children would be $191, which breaks
down to approximately $43 per week. This represents the base
4.93% for the first child plus an additional 0.675% for the
second child.
```

### Chatbot Answer
```
A family of three earning 45% of the State Median Income (SMI)
would pay **$191 per month** (or $103 per week) for the parent
share of cost when two of their children are in care.

Sources:
- Parent Share of Cost sliding‑fee‑scale table for BCY 2026,
  family size 3, 45% SMI column: monthly PSoC for two children
  is $191; weekly PSoC is $103 [Doc 1].
```

### Comparison

| Metric | Expected | Chatbot | Status |
|--------|----------|---------|--------|
| Monthly Income | $3,411 | $3,411 | ✅ Correct |
| Monthly PSoC | $191 | $191 | ✅ Correct |
| Weekly PSoC | $43 | **$103** | ❌ **Wrong** |

**The Problem:** The chatbot is reading values from the 85% SMI column instead of the 45% SMI column for the weekly amount only.

---

## Root Cause Analysis

### 1. PDF Table Structure

The source document `bcy-26-psoc-chart-twc.pdf` contains a single-page table with the following structure:

**Table Dimensions:**
- **9 columns** representing SMI percentages: 1%, 15%, 25%, 35%, **45%**, 55%, 65%, 75%, **85%**
- **4 family sizes** (2, 3, 4, 5) with multiple rows per family
- Each family size section includes:
  - Monthly income
  - Monthly PSoC - 1 Child
  - Weekly PSoC - 1 Child
  - Monthly PSoC - 2 Children
  - **Weekly PSoC - 2 Children** ← The problematic row
  - Additional rows for 3+ children

**Critical Finding:** For Family Size 3, the "Weekly PSoC - 2 Children" row contains:

| Position | SMI % | Value | Status |
|----------|-------|-------|--------|
| 1 | 1% | $0 | |
| 2 | 15% | $8 | |
| 3 | 25% | $17 | |
| 4 | 35% | $29 | |
| **5** | **45%** | **$43** | ✅ **CORRECT** |
| 6 | 55% | $61 | |
| 7 | 65% | $78 | |
| 8 | 75% | $90 | |
| **9** | **85%** | **$103** | ❌ **WRONG (what chatbot returned)** |

### 2. PDF Extraction Format Loss

When PyMuPDF extracts the table, it converts the columnar structure into vertical lists, losing the visual column alignment:

**Original Visual Layout (PDF):**
```
                1%      15%     25%     35%     45%     55%     65%     75%     85%
Monthly Income  $76    $1,137  $1,895  $2,653  $3,411  $4,169  $4,927  $5,685  $6,443
Weekly PSoC-2   $0      $8      $17     $29     $43     $61     $78     $90     $103
```

**Extracted Text (what LLM sees):**
```
Weekly PSoC - 2 Children
$0
$8
$17
$29
$43    ← Position 5 (45% SMI) - CORRECT but LLM doesn't know this
$61
$78
$90
$103   ← Position 9 (85% SMI) - WRONG but LLM reads this
```

The extracted text is just a vertical list without any indication that:
- These values correspond to different columns
- Position 5 = 45% SMI
- Position 9 = 85% SMI

### 3. Single Chunk Contains Entire Table

**Vector Database Configuration:**
- Collection: `tro-child-3-contextual`
- Chunk ID: **996** (contains the entire PSoC table)
- Reason: The PDF is only 1 page, so it becomes 1 chunk

**Chunk Contents:**
- ALL family sizes (2, 3, 4, 5)
- ALL SMI percentages (1% through 85%)
- ALL child count scenarios (1, 2, 3, 4 children)
- Both monthly and weekly amounts

**Implication:** The same chunk contains both $43 (correct) and $103 (incorrect) for the same question, creating ambiguity.

### 4. Chunk Context is Generic

The generated `chunk_context` for chunk 996:
```
Table of the 2026 Texas Parent Share of Cost (PSoC) sliding fee scale:
lists income‑percentage rates and dollar amounts for 1–4 children,
broken down by family size (2–5 members) and monthly income ranges
($62–$8,897), with corresponding monthly and weekly PSoC payments.
```

**What it does well:**
- ✅ Identifies it as a PSoC sliding fee scale table
- ✅ Mentions family sizes
- ✅ Mentions income ranges
- ✅ Notes monthly and weekly payments

**What it misses:**
- ❌ Doesn't explain the **columnar structure** (9 SMI percentage columns)
- ❌ Doesn't indicate values are **positionally organized**
- ❌ Doesn't warn about **multiple values requiring position matching**
- ❌ Doesn't mention the **income amounts as column anchors** ($3,411 = 45% SMI)

### 5. Response Generation Prompt Lacks Table Guidance

The current response generation prompt (`/chatbot/prompts/response_generation_prompt.py`):

```python
RESPONSE_GENERATION_PROMPT = """You are an expert on Texas childcare assistance programs.

Answer the question using ONLY the provided documents. Always cite sources using [Doc X] format.

Key rules:
- State income limits with exact amounts and year/BCY
- For application questions, list steps in order
- If info missing, say "I don't have information on..."
- Never make up numbers or dates
"""
```

**Missing Guidance:**
- ❌ No instructions for reading **columnar tables**
- ❌ No guidance on **counting column positions**
- ❌ No instruction to **cross-reference with row labels** (e.g., monthly income)
- ❌ No warning about **multiple values in vertical lists**

**Result:** The LLM has no framework for correctly navigating positional data in tables.

### 6. LLM Column-Reading Confusion

Based on the LLM's reasoning output (visible in test output), the model:

1. Correctly identifies the need to find PSoC for family size 3 at 45% SMI
2. Correctly locates the monthly PSoC value: $191
3. Correctly identifies the monthly income: $3,411
4. **Incorrectly** reads the weekly PSoC value as $103

**Hypotheses for why this happens:**

**Hypothesis A - Last Value Bias:**
- LLM sees the vertical list of weekly amounts
- Interprets $103 as the "maximum" or "final" value
- Associates it with 45% SMI without counting positions

**Hypothesis B - Position Counting Error:**
- LLM attempts to count positions but miscounts
- Confuses the 9th position (85% SMI) with the 5th position (45% SMI)

**Hypothesis C - Pattern Matching Error:**
- LLM successfully finds monthly income $3,411 and monthly PSoC $191
- But fails to maintain the same column position for weekly PSoC
- Reads a different position in the weekly PSoC list

**Evidence from test output:**
The LLM's reasoning states: "monthly PSoC for two children is $191; weekly PSoC is $103" and cites "45% SMI column" - showing the LLM *believes* it's reading from the 45% column but is actually reading from the 85% column.

---

## Technical Investigation

### Previous Fixes That Didn't Address This Issue

From `INVESTIGATION_REPORT.md` and `FINAL_FINDINGS.md`, several improvements were made:

1. **Chunk Ranking Issue Fixed:**
   - Problem: Relevant chunks ranking at position #33
   - Fix: Increased `RETRIEVAL_TOP_K` to 20
   - Result: ✅ Chunk 996 now ranks in top results

2. **Contextual Embeddings Implemented:**
   - Collection upgraded to `tro-child-3-contextual`
   - Chunks now include generated context
   - Result: ✅ Better retrieval relevance overall

3. **Family Size Identification Improved:**
   - Chunk context now mentions family sizes explicitly
   - Result: ✅ LLM correctly identifies "family of 3"

**However:** None of these fixes address the **column-reading problem** because:
- The retrieval phase works correctly (chunk 996 is retrieved)
- The problem occurs **during answer generation**
- The issue is **positional data interpretation**, not retrieval or context

### Current System Behavior

**Step-by-step flow for the failed question:**

1. **Query:** "How much does a family of 3 with two children in care pay at 45% SMI?"

2. **Retrieval (retriever.py):**
   - Searches Qdrant collection `tro-child-3-contextual`
   - Returns chunk 996 (PSoC table) in top results
   - ✅ **Works correctly**

3. **Reranking (reranker.py):**
   - Scores chunk 996 as highly relevant (score: 10/10)
   - ✅ **Works correctly**

4. **Generation (generator.py):**
   - Receives chunk 996 with full table data
   - Sees both $43 and $103 in the text
   - **Incorrectly selects $103** ❌
   - Returns answer with wrong weekly amount

5. **Citation:**
   - Cites "bcy-26-psoc-chart-twc.pdf, Page 0" ✅
   - Claims it read from "45% SMI column" (but actually read 85% column) ❌

### Configuration Files

**Relevant configurations:**

**`/LOAD_DB/config.py`** (Vector DB):
```python
QDRANT_COLLECTION_NAME = 'tro-child-3-contextual'
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200
```

**`/chatbot/config.py`** (Chatbot):
```python
LLM_PROVIDER = 'groq'
LLM_MODEL = 'openai/gpt-oss-20b'
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 7
```

**Note:** These configurations are appropriate for the current architecture. The issue is not with configuration but with prompt engineering and chunk context generation.

---

## Evidence

### Verification from Source PDF

**File:** `/home/tromanow/COHORT/TX/scraped_content/raw/pdfs/bcy-26-psoc-chart-twc.pdf`

**Confirmed values for Family Size 3, 45% SMI:**
```
Monthly Income: $3,411
Monthly PSoC - 1 Child: $168
Weekly PSoC - 1 Child: $38
Monthly PSoC - 2 Children: $191 ✅
Weekly PSoC - 2 Children: $43 ✅ (CORRECT)
```

**Confirmed value for Family Size 3, 85% SMI:**
```
Monthly Income: $6,443
Weekly PSoC - 2 Children: $103 ❌ (WRONG - but what chatbot returned)
```

### Chatbot's Actual Response

The chatbot's citation explicitly states:
> "45% SMI column: monthly PSoC for two children is $191; weekly PSoC is $103"

This shows:
1. The LLM correctly reads monthly PSoC from the 45% column: $191 ✅
2. The LLM incorrectly reads weekly PSoC from a different column: $103 ❌
3. The LLM believes both values came from the same column (45% SMI)

**Conclusion:** The LLM is not consistently maintaining column position when reading different rows from the same table.

---

## Recommended Solutions

### Priority 1: Enhance Response Generation Prompt (Quick Fix)

**File to modify:** `/chatbot/prompts/response_generation_prompt.py`

**Add the following guidance:**

```python
RESPONSE_GENERATION_PROMPT = """You are an expert on Texas childcare assistance programs.

Answer the question using ONLY the provided documents. Always cite sources using [Doc X] format.

Key rules:
- State income limits with exact amounts and year/BCY
- For application questions, list steps in order
- If info missing, say "I don't have information on..."
- Never make up numbers or dates

**IMPORTANT - For tables with columnar data:**
- Tables often have columns representing different categories (e.g., SMI percentages: 1%, 15%, 25%, 35%, 45%, etc.)
- When values are listed vertically, count positions carefully to match the correct column
- Use row labels as anchors (e.g., if monthly income is $3,411, that indicates the 45% SMI column)
- Verify all values (monthly, weekly, etc.) come from the SAME column position
- If you see multiple similar values, cross-reference with context clues to select the correct one
- For PSoC tables specifically: match the income amount first, then read other values from that same column
"""
```

**Expected Impact:**
- Guides LLM to use income amount ($3,411) as anchor
- Instructs LLM to maintain column consistency
- Provides explicit warning about vertical lists
- High likelihood of fixing the immediate issue

**Effort:** Low (5 minutes)
**Risk:** Low (prompt changes are easily reversible)

### Priority 2: Improve Chunk Context for Tables

**File to modify:** `/LOAD_DB/prompts/chunk_context_prompt.py`

**Current behavior:** Generic table description

**Enhanced behavior:** Detect and describe columnar structures

**Implementation approach:**

```python
# Add detection logic for columnar tables
if contains_multiple_percentage_columns(chunk_text):
    context += "\nIMPORTANT: This table has COLUMNAR structure with SMI percentage columns (1%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%). Values are listed VERTICALLY - the Nth value in each list corresponds to the Nth SMI column. Match values by column position."
```

**Example output:**
```
Table of the 2026 Texas Parent Share of Cost (PSoC) sliding fee scale:
lists income‑percentage rates and dollar amounts for 1–4 children,
broken down by family size (2–5 members) and monthly income ranges
($62–$8,897), with corresponding monthly and weekly PSoC payments.

IMPORTANT: This table has COLUMNAR structure with 9 SMI percentage
columns (1%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%). Values are
listed VERTICALLY - position 5 in any row corresponds to 45% SMI.
Use monthly income amounts as anchors to identify the correct column.
```

**Expected Impact:**
- Provides structural understanding to LLM during retrieval
- Prepares LLM for positional interpretation
- Works in conjunction with Priority 1 fix
- Helps prevent similar issues with other tables

**Effort:** Medium (2-3 hours to implement detection logic)
**Risk:** Low (additive change, doesn't break existing functionality)

### Priority 3: Add Income Cross-Reference Validation (Medium-term)

**File to modify:** `/chatbot/generator.py`

**Add post-processing validation:**

```python
def validate_psoc_answer(question, answer, sources):
    """
    Validate PSoC answers by cross-referencing income and amounts.
    If question mentions X% SMI, verify answer uses income amount
    corresponding to X% SMI.
    """
    # Extract SMI percentage from question
    smi_match = re.search(r'(\d+)%\s*SMI', question)
    if not smi_match:
        return answer  # No validation needed

    smi_percent = int(smi_match.group(1))

    # Expected monthly incomes for each SMI percentage (from PSoC table)
    # Could be loaded from config or extracted from sources
    expected_incomes = {
        # Family size 3
        (3, 45): 3411,
        (3, 85): 6443,
        # Add other family sizes and percentages...
    }

    # Check if answer contains the expected income amount
    # If not, flag for review or request regeneration

    return answer
```

**Expected Impact:**
- Catches column-reading errors automatically
- Provides safety net for future similar issues
- Can be extended to other table types

**Effort:** Medium (4-5 hours including testing)
**Risk:** Medium (requires careful testing to avoid false positives)

### Priority 4: Restructure Table Chunking (Optional, Long-term)

**File to modify:** `/LOAD_DB/load_pdf_qdrant.py`

**Current:** Single chunk contains entire table

**Proposed:** Create separate chunks for each family size + SMI percentage combination

**Example chunk structure:**
```
Chunk 996-1: "Family Size 3, 45% SMI, Monthly Income $3,411:
- 1 Child: Monthly PSoC $168, Weekly PSoC $38
- 2 Children: Monthly PSoC $191, Weekly PSoC $43
- 3 Children: Monthly PSoC $214, Weekly PSoC $49
- 4 Children: Monthly PSoC $236, Weekly PSoC $54"

Chunk 996-2: "Family Size 3, 85% SMI, Monthly Income $6,443:
- 1 Child: Monthly PSoC $451, Weekly PSoC $102
- 2 Children: Monthly PSoC $451, Weekly PSoC $103
..."
```

**Advantages:**
- Eliminates ambiguity (each chunk has only one set of values)
- Makes retrieval more precise
- Easier for LLM to extract correct values

**Disadvantages:**
- Increases number of chunks (9 SMI × 4 family sizes = 36 chunks for one table)
- May reduce context (LLM doesn't see full table structure)
- Requires custom chunking logic for table detection

**Expected Impact:**
- Highly effective at preventing column-reading errors
- May improve overall accuracy for table-based queries
- Beneficial for other complex tables in the system

**Effort:** High (2-3 days including testing and re-indexing)
**Risk:** Medium (requires re-loading entire vector database)

---

## Implementation Guidance

### Immediate Action Plan

**Step 1: Quick Fix (Priority 1)**
1. Edit `/chatbot/prompts/response_generation_prompt.py`
2. Add table-reading guidance as specified above
3. Test with the failed question
4. Verify $43 is now returned correctly

**Expected time:** 15 minutes

**Step 2: Enhanced Context (Priority 2)**
1. Edit `/LOAD_DB/prompts/chunk_context_prompt.py`
2. Add columnar structure detection
3. Regenerate contextual embeddings for PSoC table chunk
4. Re-upload to Qdrant (chunk 996 only, or full collection)
5. Test with failed question and similar table-based questions

**Expected time:** 3-4 hours

**Step 3: Monitor and Evaluate**
1. Run full evaluation suite after fixes
2. Track accuracy on table-based questions specifically
3. Document improvements in evaluation metrics
4. Decide whether Priority 3 or 4 fixes are needed

**Expected time:** 1-2 hours

### Testing Strategy

**Test cases to verify:**

1. **Original failed question:**
   ```
   Q: How much does a family of 3 with two children in care pay at 45% SMI?
   Expected: $191/month, $43/week ✅
   ```

2. **Same question, different SMI percentage:**
   ```
   Q: How much does a family of 3 with two children in care pay at 85% SMI?
   Expected: $451/month, $103/week (not $43/week!)
   ```

3. **Different family size:**
   ```
   Q: How much does a family of 4 with two children in care pay at 45% SMI?
   Expected: Should return different values than family size 3
   ```

4. **Different child count:**
   ```
   Q: How much does a family of 3 with one child in care pay at 45% SMI?
   Expected: $168/month, $38/week (not $191/$43)
   ```

5. **Edge cases:**
   ```
   Q: What is the maximum PSoC for a family of 3 with two children?
   Expected: Should return 85% SMI values: $451/month, $103/week
   ```

### Files to Modify

**Immediate fixes:**
- `/chatbot/prompts/response_generation_prompt.py` (Priority 1)
- `/LOAD_DB/prompts/chunk_context_prompt.py` (Priority 2)

**Optional enhancements:**
- `/chatbot/generator.py` (Priority 3 - validation logic)
- `/LOAD_DB/load_pdf_qdrant.py` (Priority 4 - table chunking)

### Rollback Plan

If fixes introduce regressions:

1. **Prompt changes (Priority 1, 2):**
   - Revert to previous prompt versions
   - Re-test evaluation suite
   - No database changes needed

2. **Chunk context regeneration (Priority 2):**
   - Revert to collection `tro-child-3-contextual` backup
   - Or regenerate without new context logic

3. **Table restructuring (Priority 4):**
   - Keep backup of current collection
   - Can switch between collections via config

---

## Conclusion

The chatbot's failure to return the correct weekly PSoC amount stems from a **column-reading error** in PDF table extraction, not a retrieval or ranking issue. The LLM reads from the 85% SMI column instead of the 45% SMI column when extracting the weekly amount.

**Root causes:**
1. PDF extraction loses visual column alignment
2. Chunk context doesn't describe columnar structure
3. Response generation prompt lacks table-reading guidance
4. Single chunk contains multiple similar values without positional markers

**Recommended path forward:**
1. **Immediate:** Enhance response generation prompt with table-reading instructions (**Priority 1**)
2. **Short-term:** Improve chunk context to describe columnar structure (**Priority 2**)
3. **Monitor:** Track accuracy improvements via evaluation metrics
4. **Optional:** Implement validation logic or restructure table chunking if needed (**Priority 3, 4**)

**Success criteria:**
- Failed question returns $43/week (not $103/week)
- Other table-based questions maintain or improve accuracy
- No regressions in non-table questions

---

## Appendix: Full Test Output

```
QUESTION:
How much does a family of 3 with two children in care pay at 45% SMI?

EXPECTED ANSWER:
A family of 3 at 45% SMI has a monthly income of $3,411. Their monthly
PSoC for two children would be $191, which breaks down to approximately
$43 per week. This represents the base 4.93% for the first child plus
an additional 0.675% for the second child.

CHATBOT ANSWER:
**Parent Share of Cost (PSoC) for a family of 3 with two children in
care at 45 % SMI**

| Family size | 45 % SMI monthly income | Monthly PSoC – 2 Children | Weekly PSoC – 2 Children |
|-------------|------------------------|--------------------------|--------------------------|
| 3           | $3,411                 | **$191**                 | **$103**                 |

So, a family of three earning 45 % of the State Median Income (SMI)
would pay **$191 per month** (or $103 per week) for the parent share
of cost when two of their children are in care.

**Sources**
- Parent Share of Cost sliding‑fee‑scale table for BCY 2026, family
  size 3, 45 % SMI column: monthly PSoC for two children is $191;
  weekly PSoC is $103 [Doc 1].

SOURCES:
- bcy-26-psoc-chart-twc.pdf, Page 0
```

**Analysis:**
- Monthly values correct: $3,411 income, $191 PSoC ✅
- Weekly value incorrect: $103 (should be $43) ❌
- Citation claims values from "45% SMI column" but weekly amount is from 85% SMI column
