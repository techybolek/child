# Docling Chunking Fix - Implementation Plan

**Date**: 2025-11-18
**Status**: Ready for implementation
**Priority**: High - Affects chunk quality and retrieval accuracy

---

## Executive Summary

Fix oversized chunks and semantic fragmentation in Docling-based PDF extraction while preserving table integrity. Current algorithm allows chunks up to 1659+ characters (65% over target) due to check-after-add pattern.

---

## Issues Discovered

### Context
Examined exported chunks from `evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf` against source PDF.

### Issue 1: List Formatting Lost (Docling Limitation)
- **What**: Numbered lists (1, 2, 3) and bullet points (•) removed during extraction
- **Where**: PDF pages 1-2, statutory requirements list
- **Cause**: Docling's `text_item.text` extracts plain text without preserving list markers
- **Impact**: Document structure flattened, semantic relationships lost
- **Fix**: **Cannot fix** - inherent Docling limitation
- **Workaround**: Accept trade-off (Docling's table extraction benefits outweigh list formatting loss)

### Issue 2: Semantic Fragmentation
- **What**: "Definitions" section split across 3 chunks
- **Where**: Chunk 3 (definitions 1-2), Chunk 4 (definitions 3-7), Chunk 5 (definition 8)
- **Cause**: 1000-char limit fragments related content
- **Impact**: Queries like "What definitions are provided?" may return incomplete results
- **Fix**: Check-before-add logic (partial fix - keeps related items together when possible)

### Issue 3: Oversized Chunks ⚠️ CRITICAL
- **What**: Chunk 1 is 1659 chars (65% over 1000-char target)
- **Cause**: Algorithm checks threshold AFTER adding item to buffer
- **Impact**: Inconsistent chunk sizes, potential embedding quality issues
- **Fix**: Check before adding + split large narrative items

### Issue 4: Table Formatting Errors
- **What**: Table row malformed on line 148 (`| | 2016 84.55% | 65.12% |`)
- **Cause**: Pandas DataFrame conversion via `to_markdown()`
- **Impact**: Minor - single cell boundary error
- **Fix**: **Cannot fix** - Docling upstream table parsing issue

---

## Extraction Method Clarification

**Initial Assumption**: PyMuPDF was used ❌
**Reality**: Docling is used ✅

**Evidence**: PDF is in `TABLE_PDFS` list (`LOAD_DB/config.py:45`)
- Uses Docling for extraction
- Item-level chunking (tables vs narrative)
- No character-based splitting of Docling items

---

## Root Cause Analysis

### Current Algorithm (Buggy)

**Location**: `LOAD_DB/load_pdf_qdrant.py:334-349`

```python
# CURRENT (BUGGY) LOGIC
narrative_buffer.append(item['content'])  # Add first
narrative_chars += len(item['content'])

if narrative_chars >= NARRATIVE_THRESHOLD:  # Check after
    # Too late - buffer already oversized!
    chunk_text = '\n\n'.join(narrative_buffer)
    chunks.append(create_chunk(chunk_text))
    narrative_buffer = []
    narrative_chars = 0
```

### The Problem

**Checking threshold AFTER adding allows arbitrary overflow**

**Example**:
- Buffer at 800 chars
- Next Docling item is 859 chars (large paragraph)
- Add it → buffer = 1659 chars
- Check → 1659 >= 1000 → flush **1659-char chunk** ❌

**Why this happens**:
- Docling extracts text in semantic units (paragraphs, sections)
- Algorithm never splits these units
- Only decides whether to flush AFTER adding complete item
- Result: If any single item > 1000 chars, you get oversized chunk

---

## Proposed Solution

### Two-Tier Approach

1. **Check before adding** - prevents accumulation overflow
2. **Split large items** - handles single narrative items > 1000 chars
3. **Preserve tables** - keep existing behavior (no size limit)

### Design Requirements

**Tables**:
- ✅ Always one chunk per table (no size limit)
- ✅ Preserves semantic integrity
- ✅ No changes to existing behavior

**Narrative Text**:
- ✅ Check if adding would exceed threshold
- ✅ If yes, flush buffer before adding
- ✅ If single item > 1000 chars, split using RecursiveCharacterTextSplitter
- ✅ Otherwise, accumulate normally

---

## Implementation

### File to Modify
**Path**: `LOAD_DB/load_pdf_qdrant.py`
**Method**: `create_chunks_from_items()` (lines 276-378)

### Pseudocode

```python
for item in items:
    if item['type'] == 'table':
        # UNCHANGED: Always one chunk per table (no size limit)
        # Preserves semantic integrity for tables
        if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
            flush_narrative_buffer()

        create_table_chunk(item)

    else:  # narrative text
        item_content = item['content']
        item_size = len(item_content)

        # Case 1: Single item exceeds threshold - split it
        if item_size > NARRATIVE_THRESHOLD:
            # Flush current buffer first
            if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
                flush_narrative_buffer()

            # Split large narrative item using RecursiveCharacterTextSplitter
            sub_chunks = self.text_splitter.split_text(item_content)
            for sub_chunk in sub_chunks:
                create_narrative_chunk(sub_chunk)

        # Case 2: Adding would exceed threshold - flush first
        elif narrative_chars + item_size >= NARRATIVE_THRESHOLD and narrative_buffer:
            flush_narrative_buffer()
            narrative_buffer = [item_content]
            narrative_chars = item_size

        # Case 3: Normal accumulation
        else:
            narrative_buffer.append(item_content)
            narrative_chars += item_size
```

### Implementation Details

**Helper function needed**:
```python
def flush_narrative_buffer():
    """Create chunk from current narrative buffer."""
    if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
        chunk_text = '\n\n'.join(narrative_buffer)
        chunks.append(Document(
            page_content=chunk_text,
            metadata={
                'source': pdf_path,
                'page': page_no - 1,
                'format': 'markdown',
                'extractor': 'docling',
                'chunk_type': 'narrative'
            }
        ))
        narrative_buffer.clear()
        narrative_chars = 0
```

**Access to text_splitter**:
- Already exists as `self.text_splitter` (line 98-102)
- Use `split_text()` method for character-based splitting

---

## Testing Strategy

### Phase 1: Baseline Export

**Objective**: Capture current chunk state for comparison

**Steps**:
1. Use `qdrant-file-exporter` skill
2. Export chunks for: `evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf`
3. Save to: `UTIL/evaluation_chunks_before_fix.txt`
4. Analyze:
   - Chunk sizes (min, max, avg, distribution)
   - Chunk boundaries (where splits occur)
   - Semantic coherence (definitions, sections)

**Expected findings**:
- Chunk 1: 1659 chars
- Chunks 3-5: Definitions fragmented
- Some chunks > 1500 chars

### Phase 2: Implementation

**Objective**: Modify chunking algorithm

**Steps**:
1. Back up `load_pdf_qdrant.py`
2. Modify `create_chunks_from_items()` method:
   - Add check-before-add logic (Case 2)
   - Add large-item splitting logic (Case 1)
   - Preserve table behavior (unchanged)
3. Test syntax: `python -m py_compile LOAD_DB/load_pdf_qdrant.py`
4. Review changes: Compare modified code with pseudocode

**Validation**:
- ✅ No syntax errors
- ✅ Logic matches pseudocode
- ✅ Table handling unchanged

### Phase 3: Testing

**Objective**: Test fix with surgical reload

**Steps**:
1. Verify `UTIL/reload_single_pdf.py` exists and uses contextual mode
2. Run: `python UTIL/reload_single_pdf.py evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf`
3. Monitor for:
   - Successful deletion of old chunks
   - Successful upload of new chunks
   - No errors in chunking logic
4. Check total chunk count (should be similar ±10%)

**Expected results**:
- Reload completes successfully
- Chunk count: ~43-47 chunks (vs. 43 before)
- No errors in logs

### Phase 4: Validation

**Objective**: Verify fix improves chunk quality

**Automated Checks**:

```bash
# Export chunks after fix
# Use qdrant-file-exporter skill
# Save to: UTIL/evaluation_chunks_after_fix.txt

# Compare metrics
# Max chunk size ≤ 1500 chars (99th percentile)
# Min chunk size ≥ 300 chars (except page boundaries)
# Avg chunk size ~1000-1200 chars
# Total chunks similar (±10%)
```

**Manual Review**:

Compare `evaluation_chunks_before_fix.txt` vs `evaluation_chunks_after_fix.txt`:

1. **Chunk 1**: 1659 chars → ~1000 chars ✓ (split into 2 chunks?)
2. **Definitions section**: Still split but better grouping ✓
3. **Tables**: Unchanged (preserved intact) ✓
4. **Reading order**: Preserved ✓
5. **Semantic boundaries**: Improved (fewer arbitrary splits) ✓

**Success Metrics**:
- ✅ No narrative chunks > 1500 chars
- ✅ <5% of chunks < 300 chars
- ✅ Chunk size stddev reduced by >20%
- ✅ Tables still intact
