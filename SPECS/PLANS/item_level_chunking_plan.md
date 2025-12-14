# Item-Level Chunking Implementation Plan

**Date**: 2025-11-13
**Status**: Proposed
**Priority**: High
**Estimated Effort**: 4-6 hours

## Executive Summary

Replace current page-level chunking for Docling PDFs with item-level chunking that:
1. Preserves reading order (tables appear inline, not at end)
2. Creates one chunk per semantic unit (tables, narrative sections)
3. Reduces chunk sizes from 3000+ chars to 400-1000 chars
4. Improves retrieval precision and context preservation

## Current Problems

### Problem 1: Reading Order Broken

**Issue**: Tables are appended at the END of page content, regardless of original position.

**Code Location**: `LOAD_DB/load_pdf_qdrant.py` lines 268-282
```python
# Current logic:
# 1. Collect ALL text items for page
for text_item in doc.texts:
    page_texts[page_no].append(text_item.text)

# 2. THEN append ALL tables for page
for table_item in doc.tables:
    page_texts[page_no].append(table_md)

# Result: Tables always at END
```

**Impact**:
- Page 2: 1076-char gap between "Table 1" reference and actual table
- Page 3: 1895-char gap between "Table 3A shown below" and Table 3A
- Breaks narrative flow and context

**Example from Page 3**:
```
Line 5:  "reasons for leaving care are shown below:"
Line 7:  "Table 3A - Reason for Leaving Child Care"
Lines 9-48: [1895 chars of other narrative text]
Line 49: [FINALLY Table 3A appears]
```

### Problem 2: Oversized Table Page Chunks

**Issue**: Pages with tables kept as single 3000+ char chunks.

**Current Chunk Sizes**:
- Page 2 (Chunk 7): 3021 chars (2 tables + narrative)
- Page 3 (Chunk 8): 3217 chars (2 tables + narrative)
- Pages 12-16: 2700-3000 chars each (pure table pages)

**Composition Example (Page 3, Chunk 8)**:
```
[Narrative about findings]          ~500 chars
[Narrative about TANF parents]      ~400 chars
[Narrative about Table 1]           ~200 chars
[Narrative about non-TANF]          ~400 chars
[Narrative about Table 2]           ~200 chars
[Narrative about parents leaving]   ~300 chars
[Table 3A - Leaving reasons]        ~500 chars
[Table 3B - TANF within one year]   ~400 chars
[Narrative about professional dev]  ~300 chars
TOTAL: 3217 chars in ONE chunk
```

**Impact**:
- Retrieval dilution: Query for "Table 3A" retrieves all 3217 chars
- Semantic noise: Multiple unrelated topics in same chunk
- 3x larger than optimal 1000-char target

## Proposed Solution: Item-Level Chunking

### Core Concept

**Chunk by semantic unit, not by page:**
- **Tables** → One chunk per table (preserve structure)
- **Narrative text** → Accumulate and split at ~1000 chars
- **Reading order** → Preserved via `doc.iterate_items()`

### Architecture

```
Docling Document
    ↓
doc.iterate_items() [reading order preserved]
    ↓
Process each item sequentially:
    ├─ Text item → Add to narrative buffer
    │   └─ If buffer > 1000 chars → Create chunk, flush buffer
    ├─ Table item → Flush buffer, create table chunk
    └─ Continue in reading order
    ↓
Result: Chunks in reading order, optimal sizes
```

### Expected Output

**Page 3 Example - Current vs. Proposed**:

**Current (1 chunk):**
```
Chunk 8 (3217 chars):
  - All narrative text for page
  - Table 3A (at end)
  - Table 3B (at end)
```

**Proposed (4-5 chunks):**
```
Chunk 8 (800 chars):
  "Findings\n\nEmployment and Wage Outcomes\n\nTANF Parents\n\n
   Subsidized child care is available for parents receiving TANF...
   finds employment; and maintains employment after one year.
   The five-year statewide trends are shown below:"

Chunk 9 (500 chars):
  Table 1 - Parents Receiving TANF and Child Care
  | Year | % Finding Employment | % Maintaining Employment |
  | 2012 | 81.46%              | 58.93%                   |
  | 2013 | 84.48%              | 62.07%                   |
  ...

Chunk 10 (600 chars):
  "The five-year trends by workforce areas are shown in Tables 1A and 1B...
   Non-TANF Parents\n\nSubsidized child care also provides vital work support...
   maintains the employment; and experiences a change in earnings after one year.
   The five-year statewide trends are shown in Table 2 below:"

Chunk 11 (400 chars):
  Table 2 - Working Parents Only Receiving Child Care (Non-TANF)
  | Year | % Maintaining Employment | Quarterly Change |
  | 2012 | 74.26%                  | $671.81         |
  | 2013 | 76.29%                  | $700.50         |
  ...

Chunk 12 (900 chars):
  "The five-year trends by workforce areas are shown in Tables 2A and 2B...
   Parents Leaving Child Care\n\nTexas Labor Code §302.0043(a)(3) directs TWC...
   Professional Development for Early Childhood Education\n\n
   Rider 29 of TWC's General Appropriations Act required TWC..."
```

### Chunk Size Projections

**Current**:
- evaluation PDF: 49 chunks
- Table pages: 7 chunks @ 2700-3200 chars
- Narrative pages: 42 chunks @ 700-900 chars

**Proposed**:
- evaluation PDF: ~65-70 chunks
- Tables: 9 chunks @ 400-800 chars (one per table)
- Narrative: 56-61 chunks @ 700-1000 chars
- Better granularity, same total content

## Implementation Details

### Phase 1: Update Extraction Logic

**File**: `LOAD_DB/load_pdf_qdrant.py`
**Lines**: 262-295 (replace current page-level aggregation)

**New Approach**:
```python
from docling_core.types import DocItemLabel

def extract_pdf_with_docling(self, pdf_path: str) -> List[Document]:
    """
    Extract PDF content using Docling with item-level chunking.
    Returns chunks in reading order with one chunk per semantic unit.
    """
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    # Group items by page for metadata
    page_items = {i: [] for i in range(1, doc.num_pages() + 1)}

    # Iterate through all document items in reading order
    for item in doc.iterate_items():
        if not hasattr(item, 'prov') or not item.prov:
            continue

        page_no = item.prov[0].page_no

        if item.label == DocItemLabel.TEXT:
            # Add text item with marker
            page_items[page_no].append({
                'type': 'text',
                'content': item.text,
                'prov': item.prov
            })

        elif item.label == DocItemLabel.TABLE:
            # Process table with column rotation fix
            df = item.export_to_dataframe(doc)
            df_fixed, was_fixed = fix_rotated_columns(df)
            if was_fixed:
                logger.info(f"🔧 Fixing rotated columns in table on page {page_no}")

            table_md = df_fixed.to_markdown(index=False)

            # Add table item with marker
            page_items[page_no].append({
                'type': 'table',
                'content': table_md,
                'prov': item.prov
            })

    # Convert items to chunks
    documents = []
    for page_no in range(1, doc.num_pages() + 1):
        page_docs = create_chunks_from_items(
            page_items[page_no],
            page_no,
            pdf_path
        )
        documents.extend(page_docs)

    return documents
```

### Phase 2: Chunking Logic

**New Function**:
```python
def create_chunks_from_items(items: List[Dict], page_no: int, pdf_path: str) -> List[Document]:
    """
    Create chunks from items, grouping narrative and separating tables.

    Strategy:
    - Tables: One chunk per table
    - Narrative: Accumulate until ~1000 chars, then chunk
    - Preserve reading order
    """
    chunks = []
    narrative_buffer = []
    narrative_chars = 0

    NARRATIVE_THRESHOLD = 1000
    NARRATIVE_MIN = 300  # Don't create tiny chunks

    for item in items:
        if item['type'] == 'table':
            # Flush narrative buffer first
            if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
                chunk_text = '\n\n'.join(narrative_buffer)
                chunks.append(create_document_chunk(
                    content=chunk_text,
                    page=page_no,
                    source=pdf_path,
                    chunk_type='narrative'
                ))
                narrative_buffer = []
                narrative_chars = 0

            # Create table chunk
            chunks.append(create_document_chunk(
                content=item['content'],
                page=page_no,
                source=pdf_path,
                chunk_type='table'
            ))

        elif item['type'] == 'text':
            text = item['content']
            narrative_buffer.append(text)
            narrative_chars += len(text)

            # Split narrative if over threshold
            if narrative_chars >= NARRATIVE_THRESHOLD:
                chunk_text = '\n\n'.join(narrative_buffer)
                chunks.append(create_document_chunk(
                    content=chunk_text,
                    page=page_no,
                    source=pdf_path,
                    chunk_type='narrative'
                ))
                narrative_buffer = []
                narrative_chars = 0

    # Flush remaining narrative
    if narrative_buffer and narrative_chars >= NARRATIVE_MIN:
        chunk_text = '\n\n'.join(narrative_buffer)
        chunks.append(create_document_chunk(
            content=chunk_text,
            page=page_no,
            source=pdf_path,
            chunk_type='narrative'
        ))

    return chunks

def create_document_chunk(content: str, page: int, source: str, chunk_type: str) -> Document:
    """Create a LangChain Document chunk with metadata."""
    return Document(
        page_content=content,
        metadata={
            'source': source,
            'page': page,
            'format': 'markdown',
            'extractor': 'docling',
            'chunk_type': chunk_type  # 'table' or 'narrative'
        }
    )
```

### Phase 3: Column Rotation Integration

Keep existing column rotation fix, apply to each table:

```python
def fix_rotated_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    """
    Detect and fix rotated table columns.
    Returns (fixed_df, was_fixed_bool)
    """
    if len(df.columns) < 2:
        return df, False

    last_col = df.iloc[:, -1].astype(str)
    first_col = df.iloc[:, 0].astype(str)
    first_col_name = df.columns[0]

    year_pattern = r'\b(19|20)\d{2}\b'
    has_years_in_last = last_col.str.contains(year_pattern, na=False, regex=True).sum() >= 2
    has_percentages_in_first = first_col.str.contains('%', na=False).sum() >= 2

    if has_years_in_last and has_percentages_in_first and 'year' in first_col_name.lower():
        cols = df.columns.tolist()
        df = df[[cols[-1]] + cols[:-1]]
        df.columns = cols
        return df, True

    return df, False
```

### Phase 4: Update Surgical Reload

**File**: `UTIL/reload_single_pdf.py`

Apply identical changes to maintain consistency between bulk loader and surgical reload.

## Testing Strategy

### Unit Tests

**Test 1: Reading Order Preservation**
```python
def test_reading_order():
    """Verify tables appear inline, not at end."""
    chunks = extract_pdf_with_docling('evaluation-pdf.pdf')

    # Find narrative mentioning "Table 3A shown below"
    narrative_chunk = find_chunk_containing("Table 3A shown below", chunks)

    # Find Table 3A chunk
    table_chunk = find_chunk_containing("Reason for Leaving", chunks)

    # Table should appear immediately after or within 2 chunks of reference
    assert abs(narrative_chunk.index - table_chunk.index) <= 2
```

**Test 2: Chunk Granularity**
```python
def test_chunk_sizes():
    """Verify chunk sizes are optimal."""
    chunks = extract_pdf_with_docling('evaluation-pdf.pdf')

    table_chunks = [c for c in chunks if c.metadata['chunk_type'] == 'table']
    narrative_chunks = [c for c in chunks if c.metadata['chunk_type'] == 'narrative']

    # Table chunks should be 400-1000 chars
    for chunk in table_chunks:
        assert 200 <= len(chunk.page_content) <= 1500

    # Narrative chunks should be 700-1200 chars
    for chunk in narrative_chunks:
        assert 300 <= len(chunk.page_content) <= 1500
```

**Test 3: Table Separation**
```python
def test_table_separation():
    """Verify each table is a separate chunk."""
    chunks = extract_pdf_with_docling('evaluation-pdf.pdf')

    # Page 3 has Table 3A and Table 3B
    page_3_chunks = [c for c in chunks if c.metadata['page'] == 3]
    table_chunks = [c for c in page_3_chunks if c.metadata['chunk_type'] == 'table']

    # Should have 2 separate table chunks
    assert len(table_chunks) == 2

    # Each should contain only one table
    assert table_chunks[0].page_content.count('|---|') == 1
    assert table_chunks[1].page_content.count('|---|') == 1
```

### Integration Tests

**Test 4: Full Pipeline**
```bash
# Reload evaluation PDF with new chunking
python UTIL/reload_single_pdf.py evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf

# Verify chunk count increased
# Expected: 49 → ~65-70 chunks

# Verify chunk structure
python UTIL/retrieve_chunks_by_filename.py \
  --filename "evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf" \
  --output chunks_itemlevel.json

# Analyze chunk distribution
python -c "
import json
with open('chunks_itemlevel.json') as f:
    data = json.load(f)

table_chunks = [c for c in data['chunks'] if c.get('chunk_type') == 'table']
narrative_chunks = [c for c in data['chunks'] if c.get('chunk_type') == 'narrative']

print(f'Total chunks: {len(data[\"chunks\"])}')
print(f'Table chunks: {len(table_chunks)}')
print(f'Narrative chunks: {len(narrative_chunks)}')

table_sizes = [len(c['text']) for c in table_chunks]
narrative_sizes = [len(c['text']) for c in narrative_chunks]

print(f'Table chunks avg: {sum(table_sizes)//len(table_sizes)} chars')
print(f'Narrative chunks avg: {sum(narrative_sizes)//len(narrative_sizes)} chars')
"
```

**Test 5: Retrieval Quality**
```bash
# Test specific table retrieval
python -c "
from chatbot.chatbot import TexasChildcareChatbot

chatbot = TexasChildcareChatbot(collection_name='tro-child-3-contextual')

# Query for specific table
response = chatbot.chat('What is Table 3A about?')

# Should retrieve JUST the table chunk, not entire page
print('Sources:', response['sources'])
print('First source length:', len(response['sources'][0].get('text', '')))
# Expected: ~500 chars (just table), not 3217 chars (whole page)
"
```

### Verification Checklist

- [ ] Reading order preserved (tables inline)
- [ ] Chunk count increased (~49 → ~65-70)
- [ ] Table chunks average 400-800 chars
- [ ] Narrative chunks average 700-1000 chars
- [ ] Each table is separate chunk
- [ ] Column rotation fix still works
- [ ] bcy-26 PDFs unaffected
- [ ] Retrieval precision improved
- [ ] No regression in existing functionality

## Benefits Analysis

### Quantitative Benefits

**Retrieval Precision**:
- Current: Query "Table 3A" → retrieves 3217 chars (entire page)
- Proposed: Query "Table 3A" → retrieves ~500 chars (just table)
- **Improvement**: 6.4x more focused retrieval

**Chunk Granularity**:
- Current: 7 table pages @ 2700-3200 chars
- Proposed: 9 tables @ 400-800 chars + narrative @ 700-1000 chars
- **Improvement**: 3-4x better semantic focus

**Context Preservation**:
- Current: 1895-char gap between reference and table
- Proposed: 0-200 char gap (adjacent chunks)
- **Improvement**: Context maintained

### Qualitative Benefits

1. **Better User Experience**
   - Tables cited with specific table numbers
   - Answers more focused and accurate
   - Less irrelevant content in context

2. **Improved RAG Quality**
   - Reranker has cleaner input
   - Generator receives focused context
   - Better source attribution

3. **Semantic Coherence**
   - Each chunk is single topic/unit
   - No mixing of unrelated tables
   - Clearer chunk boundaries

4. **Future Flexibility**
   - Can apply different strategies to tables vs. narrative
   - Easier to implement table-specific reranking
   - Better foundation for hybrid retrieval

## Risks and Mitigation

### Risk 1: Increased Chunk Count

**Risk**: More chunks = higher storage/processing costs

**Impact**: Low
- evaluation PDF: 49 → ~70 chunks (+43%)
- Entire collection: ~3800 → ~5300 chunks (+39%)
- Qdrant storage: Negligible (text is small)
- Embedding cost: ~$0.01 additional (one-time)

**Mitigation**: Accept - benefit far outweighs minimal cost increase

### Risk 2: Edge Cases in Narrative Buffering

**Risk**: Very short narrative sections become tiny chunks

**Impact**: Medium
- Could create 100-200 char chunks between tables

**Mitigation**:
- Set minimum chunk size (NARRATIVE_MIN = 300)
- Append short sections to previous chunk
- Log warnings for review

### Risk 3: Complex Implementation

**Risk**: More complex than current page-level approach

**Impact**: Low
- Well-defined logic (buffer/flush pattern)
- Docling API is stable
- Easy to test and verify

**Mitigation**:
- Thorough unit tests
- Gradual rollout (test on eval PDF first)
- Keep fallback to current approach

### Risk 4: Breaking Changes

**Risk**: Changes existing chunk IDs, affects evaluation history

**Impact**: Low
- Can regenerate evaluation baselines
- Only affects 3 TABLE_PDFS

**Mitigation**:
- Document breaking change
- Provide migration guide
- Reload only affected PDFs

## Rollout Plan

### Phase 1: Development (2-3 hours)
1. Implement item-level chunking in `load_pdf_qdrant.py`
2. Update `reload_single_pdf.py` with same logic
3. Add unit tests
4. Local testing on evaluation PDF

### Phase 2: Testing (1-2 hours)
1. Surgical reload of evaluation PDF
2. Verify chunk structure and sizes
3. Test retrieval quality manually
4. Check column rotation still works
5. Verify bcy-26 PDFs unaffected

### Phase 3: Validation (1 hour)
1. Run evaluation suite
2. Compare retrieval metrics
3. Spot-check specific queries
4. Document results

### Phase 4: Deployment (0.5 hour)
1. Full reload of all TABLE_PDFS
2. Update documentation
3. Commit changes

### Phase 5: Monitoring (ongoing)
1. Monitor retrieval quality
2. Check for edge cases
3. Gather user feedback
4. Iterate as needed

## Success Metrics

### Must Have
- ✅ Reading order preserved (tables inline)
- ✅ Chunk sizes: tables 400-800, narrative 700-1000
- ✅ Each table is separate chunk
- ✅ Column rotation fix still works

### Should Have
- ✅ Retrieval precision improved (smaller context windows)
- ✅ No regression in existing PDFs
- ✅ Clear chunk type metadata

### Nice to Have
- ✅ Improved evaluation scores
- ✅ Better source attribution in chatbot
- ✅ Foundation for future table-specific features

## Next Steps

1. **Review this plan** with stakeholders
2. **Approve for implementation** or request changes
3. **Assign developer** and timeline
4. **Begin Phase 1** development

## References

- [Docling Documentation](https://docling-project.github.io/docling/)
- [Docling iterate_items() API](https://docling-project.github.io/docling/reference/docling_document/)
- Current chunking implementation: `LOAD_DB/load_pdf_qdrant.py` lines 241-310
- Column rotation fix: `SPECS/chunking_strategy.md` lines 469-608
- Per-page detection fix: `SPECS/chunking_strategy.md` lines 262-304

## Appendix: Code Diff Preview

### Before (Current Approach)
```python
# Collect texts by page
for text_item in doc.texts:
    page_texts[page_no].append(text_item.text)

# Collect tables by page
for table_item in doc.tables:
    table_md = table_item.export_to_markdown()
    page_texts[page_no].append(table_md)

# Assemble pages
for page_no in range(1, num_pages + 1):
    page_content = '\n\n'.join(page_texts[page_no])
    documents.append(Document(page_content=page_content, ...))
```

### After (Item-Level Approach)
```python
# Collect items in reading order with type markers
for item in doc.iterate_items():
    if item.label == DocItemLabel.TEXT:
        page_items[page_no].append({'type': 'text', 'content': item.text})
    elif item.label == DocItemLabel.TABLE:
        df = fix_rotated_columns(item.export_to_dataframe())
        table_md = df.to_markdown(index=False)
        page_items[page_no].append({'type': 'table', 'content': table_md})

# Create chunks from items (reading order preserved, semantic units)
for page_no in range(1, num_pages + 1):
    chunks = create_chunks_from_items(page_items[page_no], ...)
    documents.extend(chunks)
```

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-13 | 1.0 | Initial plan created |
