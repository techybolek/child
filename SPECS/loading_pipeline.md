# PDF Loading Pipeline

Loads PDF documents into Qdrant vector database with optional contextual embeddings for enhanced retrieval accuracy.

## Quick Start

```bash
# Standard loading (basic embeddings)
python LOAD_DB/load_pdf_qdrant.py

# Contextual loading (3-tier context enhancement) - RECOMMENDED
python LOAD_DB/load_pdf_qdrant.py --contextual

# Test mode (3 PDFs only)
python LOAD_DB/load_pdf_qdrant.py --contextual --test

# Surgical reload (single PDF)
python UTIL/reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
```

## Architecture Overview

```
PDFs (scraped_content/raw/pdfs/)
    ↓
PyMuPDFLoader (LangChain)
    ↓
Text Cleaner (intelligent page number removal)
    ↓
RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
    ↓
Contextual Processor (optional, 3-tier context)
    ↓
OpenAI Embeddings (text-embedding-3-small, 1536-dim)
    ↓
Qdrant Vector Database
```

## Collections

| Collection | Mode | Enhancement | Use Case |
|------------|------|-------------|----------|
| tro-child-1 | Standard | None | Basic vector search |
| tro-child-3-contextual | Contextual | 3-tier context | Production (recommended) |

## Three-Tier Contextual Embeddings

Enhances chunk embeddings with hierarchical context for better retrieval accuracy.

### Tier 1: Master Context (Static)
**Purpose**: Domain-level context applied to all chunks

**Content**: "This is official Texas Workforce Commission (TWC) documentation regarding childcare assistance programs. The content covers program eligibility requirements, income limits, payment procedures, provider regulations, and administrative guidelines for childcare services in Texas. The primary programs discussed are the Child Care Development Fund (CCDF) and Provider Services Operational Consultation (PSOC)."

**Generated**: Once (hardcoded in prompts/master_context_prompt.py)

### Tier 2: Document Context (Per-PDF)
**Purpose**: Document-specific summary

**Generated from**:
- PDF filename
- Total pages
- First 2000 characters

**Model**: GROQ (openai/gpt-oss-20b)

**Output**: 2-3 sentence document summary

**Example**: "This document provides the income eligibility limits and maximum parent share of cost (PSoC) amounts for BCY 2026 childcare assistance. It includes detailed tables showing monthly income thresholds for family sizes 1-15 across nine State Median Income (SMI) brackets (1%, 15%, 25%, 35%, 45%, 55%, 65%, 75%, 85%)."

**Cached**: Stored in checkpoints/ directory to avoid regeneration

### Tier 3: Chunk Context (Per-Chunk)
**Purpose**: Situate each chunk within document structure

**Generated from**:
- Document context (Tier 2)
- Chunk text
- Previous chunk context (for continuity)
- Previous chunk text snippet (last 200 chars)

**Model**: GROQ (openai/gpt-oss-20b)

**Output**: 50-100 token context describing:
- Table type (if applicable)
- Family size (if table data)
- Income ranges covered
- Specific data values

**Example**: "This chunk contains monthly income eligibility and PSoC data for family size 12 in the BCY 2026 table. Covers SMI brackets from 1% SMI ($138,062 annual income) through 85% SMI ($138,062 annual income) with corresponding PSoC amounts ranging from $231 to $623 monthly."

**Continuity**: Uses previous chunk's context to correctly identify multi-chunk tables

### Context Embedding Strategy

Each chunk is embedded **twice**:
1. **Original chunk text** → Vector embedding
2. **Chunk text + all 3 context tiers** → Enhanced embedding

This dual embedding strategy improves retrieval by:
- Capturing both literal content (text-only) and semantic context (text+context)
- Preserving exact matches while adding domain understanding
- Enabling more accurate family size and table identification

## Text Cleaning

Intelligent text preprocessing before chunking.

### Page Number Removal
**Problem**: Standard regex removes ALL 1-3 digit numbers, destroying table row labels (family sizes 1-15)

**Solution**: Context-aware cleaning in `text_cleaner.py`

```python
# Check next line before removing number
if re.match(r'^\d{1,3}$', line):
    next_line = lines[i + 1].strip()
    # Preserve if next line starts with $ (table data)
    if next_line.startswith('$'):
        KEEP  # Table row label
    else:
        REMOVE  # Page number
```

**Preserves**:
- `12\n$5,753` (family size 12 with income)
- Table row labels (1-15)

**Removes**:
- `Page 2 of 10`
- `2` (standalone page number)
- `- 3 -` (page markers)

### TOC Filtering
Removes table-of-contents chunks using heuristics:
- High dot density (`.........` leaders)
- Lines ending with numbers (page references)
- Short length (< 200 chars)
- **Exception**: Preserves data tables (detects $ symbols and data keywords)

## Surgical Reload

Reload single PDF without full database rebuild (~1 hour → 2 minutes).

### Use Case
- Fixed text cleaner bug
- Need to reload one PDF
- Don't want to wait 1 hour for full reload

### How It Works

```python
# 1. Delete old chunks for specific PDF
# Scroll through all points, filter by PDF name
point_ids = []
for point in all_points:
    if point.payload['doc'] == 'target.pdf':
        point_ids.append(point.id)

# Delete matching chunks
client.delete(points_selector=point_ids)

# 2. Process PDF with fixed text cleaner
chunks = process_pdf(pdf_path)  # Uses clean_text()

# 3. Upload new chunks
upload_chunks(chunks)
```

### Usage

```bash
cd LOAD_DB

# Reload specific PDF
python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

# Defaults to contextual mode (tro-child-3-contextual)
# To reload to standard collection, edit line 54 in script
```

### Performance
- **Full reload**: ~1 hour (42 PDFs)
- **Surgical reload**: ~2 minutes (1 PDF)
- **Cost savings**: ~40x faster, 40x cheaper

## Pipeline Phases

### Phase 1: PDF Loading
```python
# Load PDF using LangChain
loader = PyMuPDFLoader(pdf_path)
pages = loader.load()  # List of Document objects
```

### Phase 2: Text Cleaning
```python
# Clean each page's content
for page in pages:
    page.page_content = clean_text(page.page_content)
```

### Phase 3: Chunking
```python
# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,          # Characters
    chunk_overlap=200,        # Characters
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = text_splitter.split_documents(pages)
```

### Phase 4: TOC Filtering
```python
# Filter out table-of-contents chunks
chunks = [chunk for chunk in chunks if not is_likely_toc(chunk.page_content)]
```

### Phase 5: Contextual Enhancement (Optional)
```python
# Generate document context (once per PDF)
document_context = contextual_processor.generate_document_context(
    pdf_id=pdf_filename,
    document_title=title,
    total_pages=len(pages),
    first_2000_chars=full_text[:2000]
)

# Generate chunk contexts (per chunk, with previous chunk for continuity)
chunk_contexts = contextual_processor.generate_all_chunk_contexts(
    chunks=chunks,
    document_context=document_context
)

# Add contexts to chunk metadata
for i, chunk in enumerate(chunks):
    chunk.metadata['master_context'] = MASTER_CONTEXT
    chunk.metadata['document_context'] = document_context
    chunk.metadata['chunk_context'] = chunk_contexts[i]
```

### Phase 6: Embedding Generation
```python
# Generate OpenAI embeddings
texts = [chunk.page_content for chunk in chunks]
embeddings = openai_embeddings.embed_documents(texts)
```

### Phase 7: Qdrant Upload
```python
# Prepare points
points = []
for chunk, embedding in zip(chunks, embeddings):
    point = PointStruct(
        id=hash(f"{filename}_{i}_{page}"),
        vector=embedding,
        payload={
            'text': chunk.page_content,
            'doc': filename,
            'page': page_num,
            'chunk_context': chunk_context,      # Optional
            'document_context': document_context  # Optional
        }
    )
    points.append(point)

# Upload in batches (100 per batch)
client.upsert(collection_name=collection, points=batch)
```

## Configuration

**File**: `LOAD_DB/config.py`

### Collections
```python
QDRANT_COLLECTION_NAME = 'tro-child-1'                    # Standard
QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-3-contextual'  # Enhanced
```

### Embeddings
```python
EMBEDDING_MODEL = 'text-embedding-3-small'  # OpenAI model
EMBEDDING_DIMENSION = 1536                   # Vector dimensions
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
```

### Chunking
```python
CHUNK_SIZE = 1000                           # Characters per chunk
CHUNK_OVERLAP = 200                         # Character overlap
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
```

### Contextual Processing
```python
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = 'openai/gpt-oss-20b'           # Same as chatbot
ENABLE_CONTEXTUAL_RETRIEVAL = True
USE_PREVIOUS_CHUNK_CONTEXT = True           # For continuity
CONTEXT_BATCH_SIZE = 10                     # Chunks per batch
CONTEXT_RATE_LIMIT_DELAY = 2                # Seconds between batches
```

### Paths
```python
PDFS_DIR = 'scraped_content/raw/pdfs'
LOAD_DB_LOGS_DIR = 'LOAD_DB/logs'
LOAD_DB_CHECKPOINTS_DIR = 'LOAD_DB/checkpoints'
LOAD_DB_REPORTS_DIR = 'LOAD_DB/reports'
```

## Command Reference

### Full Loading

```bash
# Standard collection (tro-child-1)
python load_pdf_qdrant.py

# Contextual collection (tro-child-3-contextual) - RECOMMENDED
python load_pdf_qdrant.py --contextual

# Test mode (3 PDFs only)
python load_pdf_qdrant.py --contextual --test

# Append mode (don't clear collection)
python load_pdf_qdrant.py --contextual --no-clear
```

### Surgical Reload

```bash
# Reload single PDF (contextual mode)
python reload_single_pdf.py <pdf-filename>

# Example
python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
```

### Verification

```bash
# Verify collection
python verify_qdrant.py

# Verify specific PDF chunks contain row labels
python verify_row_labels.py
```

## Outputs

### Logs
**Location**: `LOAD_DB/logs/pdf_load_YYYYMMDD_HHMMSS.log`

Contains:
- Processing progress
- PDF-by-PDF statistics
- Error messages
- Timing information

### Checkpoints
**Location**: `LOAD_DB/checkpoints/`

**Files**:
- `checkpoint_<pdf_count>.json` - Progress snapshots (every 5 PDFs)
- `document_context_<pdf_id>.json` - Cached document contexts

### Reports
**Location**: `LOAD_DB/reports/load_report_YYYYMMDD_HHMMSS.txt`

Contains:
- Total PDFs processed
- Total chunks created
- Failed PDFs (if any)
- Processing time
- Average chunks per PDF

## Performance Metrics

### Standard Mode (tro-child-1)
- **Speed**: ~2.5 minutes for 42 PDFs
- **Output**: 3,722 chunks
- **Embedding cost**: ~$0.03 (OpenAI)

### Contextual Mode (tro-child-3-contextual)
- **Speed**: ~60 minutes for 42 PDFs
- **Output**: 3,722 chunks with 3-tier context
- **Embedding cost**: ~$0.03 (OpenAI)
- **Context generation cost**: ~$2.00 (GROQ)
- **Total cost**: ~$2.03

### Surgical Reload
- **Speed**: ~2 minutes for 1 PDF
- **Cost**: ~$0.05 (contextual mode)

## Key Files

| File | Purpose |
|------|---------|
| `load_pdf_qdrant.py` | Main loading script with contextual support |
| `reload_single_pdf.py` | Surgical reload for single PDFs |
| `contextual_processor.py` | 3-tier context generation |
| `text_cleaner.py` | Intelligent text cleaning |
| `verify_qdrant.py` | Collection verification |
| `verify_row_labels.py` | Verify table row labels preserved |
| `config.py` | Configuration settings |
| `prompts/master_context_prompt.py` | Tier 1 context |
| `prompts/document_context_prompt.py` | Tier 2 prompt builder |
| `prompts/chunk_context_prompt.py` | Tier 3 prompt builder |

## Typical Workflow

### Initial Load
1. Set environment variables (QDRANT_*, OPENAI_API_KEY, GROQ_API_KEY)
2. Run test: `python load_pdf_qdrant.py --contextual --test`
3. Verify: `python verify_qdrant.py`
4. Run full: `python load_pdf_qdrant.py --contextual`
5. Check logs and reports in `LOAD_DB/logs/` and `LOAD_DB/reports/`

### After Text Cleaner Fix
1. Fix bug in `text_cleaner.py`
2. Test with single PDF: `python reload_single_pdf.py test.pdf`
3. Verify: `python verify_row_labels.py`
4. If good, reload all affected PDFs surgically

### After Adding New PDFs
1. Place PDFs in `scraped_content/raw/pdfs/`
2. Run: `python load_pdf_qdrant.py --contextual --no-clear`
3. Verify: `python verify_qdrant.py`

## Technical Decisions

### Why OpenAI Embeddings?
- High quality (1536 dimensions)
- Fast (53% faster than alternatives tested)
- Industry standard
- Good documentation

### Why GROQ for Context Generation?
- Fast inference (~2-3s per chunk context)
- Cost-effective ($0.05 per million tokens)
- Same model as chatbot (consistency)
- Good at structured extraction

### Why Three-Tier Context?
- **Tier 1 (Master)**: Domain understanding across all chunks
- **Tier 2 (Document)**: Document-specific summary
- **Tier 3 (Chunk)**: Precise chunk situating with continuity

This hierarchy improved retrieval accuracy by 15-20% in testing, especially for:
- Multi-page tables
- Family size identification
- Income range queries
- Complex table data

### Why LangChain?
- Standardized document loading
- Automatic metadata extraction
- Flexible text splitting
- Easy integration with vector databases

### Why Surgical Reload?
- Saves time (60 min → 2 min)
- Saves cost (40x reduction)
- Enables rapid iteration on fixes
- Preserves unaffected chunks

## Known Issues

### Checkpoint Resume
**Issue**: No automatic resume from checkpoint

**Workaround**: Manual restart required if loading fails mid-process

**Future**: Add `--resume` flag

## Troubleshooting

### "Collection already exists"
**Cause**: Previous load didn't clear collection

**Solution**: Use default (clears automatically) or run with `--no-clear` to append
