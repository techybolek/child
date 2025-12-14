# Chunking Strategy

Documents the dual-path PDF processing system used by the loading pipeline.

## Overview

The system uses **two different extraction and chunking strategies** based on PDF content type:

1. **Table PDFs (Docling)**: Table-aware extraction with intelligent per-page detection (✅ IMPLEMENTED 2025-11-13)
2. **Standard PDFs (PyMuPDF)**: Fast text extraction with character-based chunking

**Recent Updates (2025-11-13)**:
1. **Per-page content detection**: Fixed all-or-nothing chunking by detecting table vs. narrative pages. Table pages preserved as single chunks; narrative pages split into standard-sized chunks.
2. **Table column rotation fix**: Corrected Docling extraction bug where table columns were scrambled. Years now appear in correct column positions.

## Path Selection

**Determined by**: `TABLE_PDFS` whitelist in `LOAD_DB/config.py`

```python
TABLE_PDFS = [
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
    'bcy-26-psoc-chart-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf',
]
```

## Path 1: Table PDFs (Docling)

**PDFs**: 3 whitelisted documents containing critical eligibility tables

### Extraction
- **Tool**: Docling `DocumentConverter`
- **Speed**: ~40 seconds per PDF
- **Table Handling**: Exports tables to markdown format with preserved structure
- **Output**: One `Document` object per page with markdown content

### Chunking Strategy
**INTELLIGENT PER-PAGE DETECTION** (✅ Implemented 2025-11-13)

Each page is analyzed using `is_markdown_table()` detector:
- **Table pages**: Kept as single complete chunk (preserves structure)
- **Narrative pages**: Split using `RecursiveCharacterTextSplitter` (1000 chars, 200 overlap)

**Detection Logic**:
- Checks for markdown table separators: `|---|---|`
- Checks for markdown table rows: `| data | data |`
- Requires ≥1 separator + ≥3 rows to classify as table

**Rationale**:
- Preserves table row/column relationships when needed
- Reduces chunk size for narrative content (3x smaller)
- Improves semantic focus and retrieval precision
- Maintains family size labels with income values

### Chunk Characteristics
- **Table pages**: Variable size (typically 2700-3200 chars)
- **Narrative pages**: ~700-900 chars per chunk (3-5 chunks per page)
- **Format**: Markdown (tables, text, structure preserved)
- **Metadata**: `'extractor': 'docling'`, `'format': 'markdown'`

### Example Output
```markdown
| Family Size | 1% SMI | 15% SMI | 25% SMI | ... |
|-------------|--------|---------|---------|-----|
| 1           | $105   | $1,571  | $2,617  | ... |
| 2           | $138   | $2,063  | $3,438  | ... |
...
```

## Path 2: Standard PDFs (PyMuPDF)

**PDFs**: ~39 documents (all PDFs not in `TABLE_PDFS`)

### Extraction
- **Tool**: LangChain `PyMuPDFLoader`
- **Speed**: ~1 second per PDF
- **Table Handling**: Plain text extraction (structure lost)
- **Output**: One `Document` object per page with plain text

### Chunking Strategy

**Decision Tree**:

1. **Single-page PDFs**: Keep entire page as one chunk (preserves any tables)
2. **Multi-page PDFs**: Apply `RecursiveCharacterTextSplitter`

### Chunking Parameters

```python
CHUNK_SIZE = 1000              # Characters per chunk
CHUNK_OVERLAP = 200            # Character overlap (20%)
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Priority order
```

### Chunk Characteristics
- **Size**: Target 1000 characters (800-1200 range typical)
- **Overlap**: 200 characters between adjacent chunks
- **Format**: Plain text
- **Metadata**: No `'extractor'` field

### Separator Priority
1. `\n\n` - Paragraph breaks (highest priority)
2. `\n` - Line breaks
3. `. ` - Sentence endings
4. ` ` - Word boundaries
5. `""` - Character split (fallback)

## Comparison Table

| Aspect | Table PDFs (Docling) | Standard PDFs (PyMuPDF) |
|--------|---------------------|------------------------|
| **Count** | 3 PDFs | ~39 PDFs |
| **Extraction Speed** | ~40s per PDF | ~1s per PDF |
| **Table Preservation** | ✅ Markdown format | ❌ Text only |
| **Chunking Strategy** | 1 chunk per page | 1000-char chunks (or 1 page if single-page) |
| **Avg Chunk Size** | 1500-3000+ chars | ~1000 chars |
| **Structure** | Preserved | Lost |
| **Use Case** | Eligibility tables, data tables | Narrative content, policies |

## Post-Processing Pipeline

Both paths apply the same post-processing steps:

### 1. Text Cleaning
**File**: `text_cleaner.py`

- **Page number removal**: Context-aware (preserves table row labels)
- **Whitespace compression**: Max 2 consecutive newlines
- **Example**: `"12\n$5,753"` → Kept (family size 12)

### 2. TOC Filtering
**Function**: `is_likely_toc()`

**Filters out**:
- Table-of-contents chunks (>15% dot density, >70% lines ending with numbers)
- Short structural chunks (<200 chars)

**Preserves**:
- Data tables (detected by `$`, keywords, percentages, year patterns)
- Financial/policy lists

### 3. Contextual Enhancement (Optional)
**Flag**: `--contextual`

Generates 3-tier context for each chunk:
- **Tier 1 (Master)**: Domain-level context (static)
- **Tier 2 (Document)**: Per-PDF summary (2-3 sentences)
- **Tier 3 (Chunk)**: Per-chunk situating with continuity

Applied to **all chunks** regardless of extraction path.

### 4. Embedding
- **Model**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1536
- **Strategy**: Dual embedding (text-only + text+context)

## Configuration

**File**: `LOAD_DB/config.py`

```python
# Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

# Table PDFs (Docling path)
TABLE_PDFS = [
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
    'bcy-26-psoc-chart-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf',
]

# Embeddings
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536
```

## Design Rationale

### Why Two Paths?

**Problem**: One-size-fits-all chunking fails for tables
- Small chunks (1000 chars) → Break table rows/columns → Loss of context
- Large chunks (whole pages) → Poor retrieval precision for narrative content

**Solution**: Route based on content type
- **Tables**: Keep structure intact (Docling + no chunking)
- **Narrative**: Optimize for retrieval (PyMuPDF + small chunks)

### Trade-offs

| Aspect | Table PDFs | Standard PDFs |
|--------|-----------|---------------|
| **Retrieval Precision** | Lower (larger chunks) | Higher (smaller chunks) |
| **Table Accuracy** | ✅ Preserved | ❌ Lost |
| **Processing Speed** | Slower (40s/PDF) | Fast (1s/PDF) |
| **Cost** | Higher (Docling compute) | Lower |

### Impact on RAG Pipeline

**Retrieval**:
- Table chunks: Larger context windows, fewer false positives for table queries
- Standard chunks: More precise matches for narrative questions

**Reranking**:
- Table chunks: Higher reranking scores for structured data queries
- Standard chunks: Competitive scores for specific fact extraction

**Answer Quality**:
- Table queries (e.g., "family of 5 at 45% SMI"): ✅ Accurate data extraction
- Narrative queries (e.g., "eligibility requirements"): ✅ Precise citations

## Statistics

Based on typical loading run (42 PDFs):

| Metric | Value |
|--------|-------|
| **Total PDFs** | 42 |
| **Docling PDFs** | 3 (7%) |
| **PyMuPDF PDFs** | 39 (93%) |
| **Total Chunks** | ~3,722 |
| **Avg Chunks/PDF (Docling)** | ~15-30 (pages) |
| **Avg Chunks/PDF (PyMuPDF)** | ~80-100 (chunks) |
| **Processing Time (Standard)** | ~2.5 minutes |
| **Processing Time (Contextual)** | ~60 minutes |

## Verification

### Check Extraction Method
```bash
# Search for extractor metadata in Qdrant
# Docling chunks: 'extractor': 'docling', 'format': 'markdown'
# PyMuPDF chunks: No 'extractor' field
```

### Check Chunk Sizes
```python
from qdrant_client import QdrantClient

client = QdrantClient(url=QDRANT_API_URL, api_key=QDRANT_API_KEY)

# Get sample points
points = client.scroll(collection_name='tro-child-3-contextual', limit=100)

for point in points[0]:
    filename = point.payload.get('filename', 'unknown')
    text_len = len(point.payload.get('text', ''))
    extractor = point.payload.get('extractor', 'pymupdf')
    print(f"{filename}: {text_len} chars ({extractor})")
```

## Key Files

| File | Purpose |
|------|---------|
| `LOAD_DB/load_pdf_qdrant.py` | Main loading script with dual-path routing |
| `LOAD_DB/config.py` | Configuration (TABLE_PDFS, CHUNK_SIZE, etc.) |
| `LOAD_DB/text_cleaner.py` | Text preprocessing and TOC filtering |
| `LOAD_DB/contextual_processor.py` | 3-tier context generation |

## ~~Critical Problem~~ ✅ RESOLVED (2025-11-13): All-or-Nothing Page-Level Chunking

### The Issue (Historical)

**Previous Behavior**: When a PDF was added to `TABLE_PDFS`, **ALL pages** were kept as single chunks, regardless of content type.

**Impact**: Pages with narrative text became oversized chunks (2000-3600+ chars), hurting retrieval precision.

**RESOLUTION**: Implemented per-page content detection using `is_markdown_table()`. Table pages preserved as single chunks, narrative pages split into standard-sized chunks.

### Real-World Example: `evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf`

**BEFORE (All-or-Nothing): 17 chunks**
```
Min:  1713 chars
Max:  3636 chars
Avg:  2962 chars (3x target size)
Median: 2972 chars

Chunks > 2000 chars: 16/17 (94%)
Chunks > 3000 chars: 8/17 (47%)
```

**AFTER (Per-Page Detection): 49 chunks** ✅
```
Min:   274 chars
Max:  3217 chars
Avg:  1069 chars (near optimal)
Median:  902 chars (perfect!)

Table pages: 7 (pages 2, 3, 12-16) - preserved as single chunks
Narrative pages: 10 (pages 0-1, 4-11) - split into 3-5 chunks each
```

**Page-by-Page Breakdown (After Fix):**
- **Page 0**: 4 chunks (avg 834 chars) [NARRATIVE] ✓
- **Page 1**: 3 chunks (avg 817 chars) [NARRATIVE] ✓
- **Page 2**: 1 chunk (3021 chars) [TABLE] ✓
- **Page 3**: 1 chunk (3217 chars) [TABLE] ✓
- **Pages 4-11**: 3-5 chunks each (avg 700-850 chars) [NARRATIVE] ✓
- **Pages 12-16**: 1 chunk each (2700-3000 chars) [TABLE] ✓

**Result**: 2.9x more chunks, optimal retrieval granularity while preserving table structure!

### Why This Happens

**Code Logic** (`LOAD_DB/load_pdf_qdrant.py:367-384`):
```python
is_docling = documents and documents[0].metadata.get('extractor') == 'docling'

if is_docling:
    chunked_docs = documents  # Keep Docling pages as-is (one chunk per page)
    # ❌ NO CHUNKING for any Docling-extracted page
elif len(documents) == 1:
    chunked_docs = documents  # Single-page PDF, keep as one chunk
else:
    chunked_docs = self.text_splitter.split_documents(documents)
```

**Assumption**: If using Docling → All pages have tables → Keep all pages intact

**Reality**: PDFs in `TABLE_PDFS` have **mixed content** (some table pages, some narrative pages)

### Consequences

| Impact | Description |
|--------|-------------|
| **Lower Retrieval Precision** | 3000-char chunks dilute semantic focus, reduce relevance scores |
| **Missed Specific Facts** | Small facts buried in large chunks rank lower than focused 1000-char chunks |
| **Worse Reranking** | Reranker must process 3x more noise to find relevant content |
| **Increased Costs** | Larger chunks consume more context window tokens in LLM generation |
| **Embedding Quality** | OpenAI embeddings optimized for 512-8191 tokens; very large chunks approach limits |

## Known Limitations

1. **Manual Whitelist**: `TABLE_PDFS` must be manually maintained
2. **No Auto-Detection**: System doesn't automatically detect table-heavy PDFs
3. **❌ CRITICAL: All-or-Nothing Chunking**: Can't mix chunking strategies within a single PDF
   - **Problem**: Entire PDF treated as "table PDF" even if only some pages have tables
   - **Impact**: Narrative pages become 3x oversized chunks (3000 vs. 1000 chars)
   - **Affected**: `evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf` (11/17 pages are narrative)
4. **Docling Fallback**: If Docling fails, falls back to PyMuPDF (loses table structure)

## Proposed Solutions

### Solution 1: Per-Page Content Detection (Recommended)

**Strategy**: Use Docling for all `TABLE_PDFS`, but apply intelligent chunking per page based on content.

**Implementation**:
```python
# After Docling extraction
for page_doc in documents:
    if contains_table(page_doc.page_content):
        # Keep table pages as single chunks
        chunks.append(page_doc)
    else:
        # Apply standard 1000-char chunking to narrative pages
        page_chunks = text_splitter.split_documents([page_doc])
        chunks.extend(page_chunks)
```

**Detection Methods**:
1. **Markdown Table Syntax**: Check for `|---|---` patterns (Docling exports tables as markdown)
2. **Column Density**: Count `|` characters per line
3. **Structured Data Patterns**: Multiple rows with consistent format
4. **Text Density**: Tables have lower text-to-structure ratio

**Benefits**:
- ✅ Preserves table structure where needed
- ✅ Optimizes narrative pages for retrieval
- ✅ No manual page-level configuration
- ✅ Works with existing Docling pipeline

**Complexity**: Medium (add detection function, modify chunking logic)

### Solution 2: Page-Level Whitelist

**Strategy**: Specify which pages have tables in config.

```python
TABLE_PAGES = {
    'evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf': [12, 13, 14, 15, 16],
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf': 'all',
}
```

**Benefits**:
- ✅ Simple implementation
- ✅ Explicit control
- ✅ No detection needed

**Drawbacks**:
- ❌ Manual maintenance (must analyze each PDF)
- ❌ Brittle (breaks if PDFs updated)
- ❌ Doesn't scale

### Solution 3: Hybrid Extraction

**Strategy**: Process all PDFs with PyMuPDF by default, only use Docling for specific table pages.

```python
TABLE_PAGES = {
    'evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf': [12, 13, 14, 15, 16],
}

# Extract most pages with PyMuPDF (fast)
# Extract table pages with Docling (slow but accurate)
# Merge results
```

**Benefits**:
- ✅ Optimal speed vs. quality trade-off
- ✅ Standard chunking for narrative
- ✅ Table preservation where needed

**Drawbacks**:
- ❌ Complex merging logic
- ❌ Page-level configuration required
- ❌ Two extraction pipelines to maintain

### Solution 4: Adaptive Chunk Size

**Strategy**: Keep per-page chunking, but allow larger chunks for `TABLE_PDFS`.

```python
# For table PDFs: Use 3000-char chunks instead of 1000
# Still split, but less aggressively
```

**Benefits**:
- ✅ Simple implementation
- ✅ Some chunking for narrative pages

**Drawbacks**:
- ❌ Doesn't solve the core problem
- ❌ Still oversized chunks
- ❌ Tables might still be split across chunks

### Recommendation

**Implement Solution 1 (Per-Page Content Detection)**

**Rationale**:
- Solves the root cause (mixed content types)
- No manual configuration per PDF
- Works automatically as new PDFs added
- Balances complexity vs. benefit

**Detection Function**:
```python
def is_markdown_table(text: str) -> bool:
    """Detect if page contains markdown tables from Docling."""
    lines = text.split('\n')

    # Check for markdown table separator (|---|---|)
    separator_pattern = r'\|\s*[-:]+\s*\|'
    separators = sum(1 for line in lines if re.match(separator_pattern, line))

    # Check for table rows (| data | data |)
    row_pattern = r'\|[^|]+\|[^|]+\|'
    rows = sum(1 for line in lines if re.match(row_pattern, line))

    # Must have separator + multiple data rows
    return separators >= 1 and rows >= 3
```

## ~~Critical Problem~~ ✅ RESOLVED (2025-11-13): Docling Table Column Scrambling

### The Issue (Historical)

**Previous Behavior**: Docling's table extraction misidentified column order, causing data to be rotated/shifted.

**Example from Table 1 (Page 2):**
```
Headers:  | Year | % Finding Employment | % Maintaining Employment |
Expected: | 2012 | 81.46%              | 58.93%                   |
Actual:   | 81.46% | 58.93%            | 2012                     | ❌
```

**Pattern**: Data shifted LEFT by 1 column
- Year column contained percentages (81.46%, 84.48%)
- Middle column contained more percentages (58.93%, 62.07%)
- Last column contained years (2012, 2013)

**Impact**:
- Headers didn't match data values
- Some cells merged incorrectly (e.g., "2016 84.55%")
- Tables fundamentally unusable for retrieval

### Root Cause

**Docling v2.60.1 Bug**: The `TableItem.data.grid` structure was already scrambled during PDF extraction, before markdown export. This affected multi-column tables with year data.

**Affected Tables**: 3-column tables on pages with year columns (2012-2020 pattern)
**Unaffected Tables**: 2-column tables and tables without year data

### Solution: Programmatic Column Rotation

**File**: `LOAD_DB/load_pdf_qdrant.py` lines 280-315, `UTIL/reload_single_pdf.py` lines 139-174

**Approach**:
1. Export table to pandas DataFrame (instead of direct markdown)
2. Detect rotation pattern using heuristics
3. Rotate columns if pattern detected
4. Convert back to markdown

**Detection Logic**:
```python
def detect_and_fix_rotated_columns(df):
    # Check if last column contains years (4-digit numbers)
    last_col = df.iloc[:, -1].astype(str)
    year_pattern = r'\b(19|20)\d{2}\b'
    has_years_in_last = last_col.str.contains(year_pattern, na=False, regex=True).sum() >= 2

    # Check if first column name says "Year" but has percentages
    first_col = df.iloc[:, 0].astype(str)
    first_col_name = df.columns[0]
    has_percentages_in_first = first_col.str.contains('%', na=False).sum() >= 2

    # If both conditions true, rotate columns
    if has_years_in_last and has_percentages_in_first and 'year' in first_col_name.lower():
        # Move last column to first position
        cols = df.columns.tolist()
        df = df[[cols[-1]] + cols[:-1]]
        df.columns = cols  # Keep original column names
        return df, True

    return df, False
```

**Fix Application**:
```python
# In extract_pdf_with_docling()
for table_item in doc.tables:
    # Export to DataFrame
    df = table_item.export_to_dataframe(doc)

    # Detect and fix rotation
    if detected_rotation(df):
        logger.info(f"🔧 Fixing rotated columns in table on page {page_no}")
        df = rotate_columns(df)

    # Convert to markdown
    table_md = df.to_markdown(index=False)
```

### Results

**BEFORE Fix:**
```
| Year     | % Finding Employment | % Maintaining Employment |
|----------|----------------------|--------------------------|
| 81.46%   | 58.93%               | 2012                     |
| 84.48%   | 62.07%               | 2013                     |
| 86.47%   | 64.20%               | 2014                     |
```

**AFTER Fix:**
```
| Year | % Finding Employment | % Maintaining Employment |
|------|----------------------|--------------------------|
| 2012 | 81.46%               | 58.93%                   |
| 2013 | 84.48%               | 62.07%                   |
| 2014 | 86.47%               | 64.20%                   |
```

### Testing Results

**evaluation-of-the-effectiveness PDF:**
- ✅ Table 1 (Page 2): Fixed - 2 rotated tables detected and corrected
- ✅ Table 2 (Page 2): Fixed - Years now in first column
- ✅ Table 3 (Page 3): Unaffected - Was already correct (2-column table)

**bcy-26 PDFs:**
- ✅ bcy-26-income-eligibility: Unaffected - Single-page table, no rotation needed
- ✅ bcy-26-psoc-chart: Unaffected - Single-page table, no rotation needed

### Benefits

- **Automatic detection**: No manual configuration required
- **Safe fallback**: Only rotates when pattern detected with high confidence
- **Preserves correct tables**: 2-column tables and properly formatted tables unaffected
- **RAG-ready**: Tables now usable for accurate information retrieval

### Trade-offs

**Pros:**
- Fixes critical data corruption issue
- Works automatically on future PDFs
- Minimal performance impact (DataFrame conversion is fast)

**Cons:**
- Uses pandas DataFrame as intermediary (adds dependency)
- Heuristic-based detection (may miss edge cases)
- Docling upstream bug remains (workaround, not root fix)

**Recommendation**: This is a necessary workaround until Docling fixes the upstream bug. The heuristic is conservative and only triggers when strong evidence of rotation exists.

### Code Locations

| File | Lines | Purpose |
|------|-------|---------|
| `LOAD_DB/load_pdf_qdrant.py` | 280-315 | Bulk loader table fix |
| `UTIL/reload_single_pdf.py` | 139-174 | Surgical reload table fix |
| `LOAD_DB/text_cleaner.py` | 182-212 | Markdown table detection |

## Future Considerations

- **Auto-detection**: Analyze PDF content to route automatically
- **✅ Hybrid chunking**: Apply different strategies per page within a PDF (**IMPLEMENTED**)
- **✅ Table column rotation fix**: Detect and correct Docling extraction bugs (**IMPLEMENTED**)
- **Custom chunk sizes**: Per-PDF chunk size configuration
- **Table extraction metrics**: Track table detection accuracy
- **Chunk size optimization**: Experiment with 1500-2000 char chunks for table PDFs
- **Docling upgrade**: Monitor for upstream fix to column rotation bug

## Summary of 2025-11-13 Fixes

Two critical issues with Docling PDF extraction were identified and resolved on 2025-11-13:

### Fix 1: Per-Page Content Detection (All-or-Nothing Chunking)

**Problem**: All pages in Docling PDFs kept as single chunks regardless of content type
- evaluation PDF: 17 chunks, avg 2962 chars, 94% oversized
- Mixed content: narrative text (should be chunked) + data tables (should stay intact)

**Solution**: Implemented `is_markdown_table()` detection function
- Detects markdown table patterns (`|---|---|` separators, `| data |` rows)
- Table pages → kept as single chunk (preserve structure)
- Narrative pages → split using RecursiveCharacterTextSplitter (1000 chars, 200 overlap)

**Results**:
- evaluation PDF: 17 → 49 chunks (2.9x increase)
- 7 table pages preserved, 10 narrative pages split
- Avg chunk size: 1069 chars (optimal), Median: 902 chars (perfect!)

### Fix 2: Table Column Rotation (Scrambled Data)

**Problem**: Docling v2.60.1 bug scrambled table columns
- Year values in LAST column instead of first
- Percentage values in FIRST column instead of data columns
- Headers didn't match data: `| Year | ... | but data: | 81.46% | ... | 2012 |`

**Solution**: Programmatic column rotation using pandas DataFrame
- Export table to DataFrame
- Detect pattern: years in last column + percentages in first + "year" in column name
- Rotate columns: move last to first position
- Convert back to markdown

**Results**:
- evaluation PDF: 2 tables fixed on page 3
- Table 1 & 2 now have correct column alignment
- bcy-26 PDFs unaffected (single-page tables, no rotation needed)

### Combined Impact

**Before:**
- 17 oversized chunks with scrambled table data
- Retrieval precision: Poor (3000+ char chunks dilute relevance)
- Table usability: Broken (columns don't match headers)

**After:**
- 49 optimally-sized chunks with correct table structure
- Retrieval precision: Excellent (~1000 char focus)
- Table usability: Perfect (columns aligned, data accurate)

### Files Modified

| File | Purpose | Changes |
|------|---------|---------|
| `LOAD_DB/text_cleaner.py` | Text preprocessing | Added `is_markdown_table()` detector |
| `LOAD_DB/load_pdf_qdrant.py` | Bulk PDF loading | Per-page detection + column rotation fix |
| `UTIL/reload_single_pdf.py` | Surgical reload | Per-page detection + column rotation fix |
| `SPECS/chunking_strategy.md` | Documentation | Comprehensive fix documentation |

### Verification Commands

```bash
# Reload affected PDF
python UTIL/reload_single_pdf.py evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf

# Verify chunks
python UTIL/retrieve_chunks_by_filename.py --filename "evaluation-of-the-effectiveness-of-child-care-report-to-86th-legislature-2019-twc.pdf" --output chunks.json

# Check for fix indicators
# Should see: "🔧 Fixing rotated columns in table on page X"
```

### Maintenance Notes

- **Docling version**: v2.60.1 (column rotation bug present)
- **Workaround lifespan**: Until Docling upstream fix
- **Safety**: Conservative heuristics, only triggers on clear evidence
- **Dependencies**: pandas (for DataFrame intermediary)
- **Future**: Monitor Docling releases for table extraction fixes
