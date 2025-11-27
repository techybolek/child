# PDF Loading Pipeline

Loads PDF documents into Qdrant vector database with hybrid embeddings and optional contextual enhancement.

## Quick Start

```bash
cd LOAD_DB

# Standard loading with contextual embeddings (recommended)
python load_pdf_qdrant.py --contextual

# Test mode (3 PDFs only)
python load_pdf_qdrant.py --contextual --test

# Surgical reload (single PDF)
python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
```

## Architecture

```
PDFs (scraped_content/raw/pdfs/)
    ↓
Extractor Selection (PyMuPDF or Docling based on TABLE_PDFS)
    ↓
Text Cleaner (page numbers, footers, TOC removal)
    ↓
RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
    ↓
Contextual Processor (optional, 3-tier context via GROQ)
    ↓
Embedding Generation
    ├── Dense: OpenAI text-embedding-3-small (1536-dim)
    └── Sparse: BM25 (vocabulary 30,000)
    ↓
Qdrant Upload (tro-child-hybrid-v1)
```

## Collection

**Name:** `tro-child-hybrid-v1`

**Schema:** Unified hybrid with named vectors:
- `dense` - OpenAI embeddings (1536 dimensions)
- `sparse` - BM25 keyword vectors

**Metadata Fields:**
- `text` - Chunk content
- `doc` - Source PDF filename
- `page` - Page number
- `source_url` - Original URL (if available)
- `master_context` - Tier 1 context (optional)
- `document_context` - Tier 2 context (optional)
- `chunk_context` - Tier 3 context (optional)

## Three-Tier Contextual Embeddings

Enhances retrieval accuracy by adding hierarchical context to embeddings.

### Tier 1: Master Context (Static)
Domain-level context applied to all chunks. Hardcoded description of TWC childcare programs.

### Tier 2: Document Context (Per-PDF)
Generated once per PDF from:
- PDF filename
- Total pages
- First 2000 characters

Cached in `checkpoints/doc_context_{pdf_id}.json`

### Tier 3: Chunk Context (Per-Chunk)
Generated for each chunk with previous chunk context for continuity. Includes:
- Table type identification
- Family size (for table data)
- Income ranges covered
- Specific data values

**Model:** GROQ `openai/gpt-oss-20b`

## Two-Tier Extraction

### PyMuPDF (Default)
- Speed: ~1 second per PDF
- Uses LangChain `PyMuPDFLoader`
- Character-based chunking with overlap
- Good for narrative documents

### Docling (Table PDFs)
- Speed: ~40 seconds per PDF
- Configured in `config.TABLE_PDFS`:
  - `bcy-26-income-eligibility-and-maximum-psoc-twc.pdf`
  - `bcy-26-psoc-chart-twc.pdf`
  - `evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf`
- Item-level chunking (semantic units)
- Tables extracted as markdown
- No overlap (relies on semantic boundaries)

## Text Cleaning

### Page Number Removal
Context-aware cleaning preserves table row labels:
```python
# Removes: "Page 2 of 10", standalone "2", "- 3 -"
# Preserves: "12\n$5,753" (family size with income data)
```

### Footer Removal
Removes agency footers: TWC, HHSC, DFPS, "Report - Nth Legislature"

### TOC Detection
Multi-signal detection (6+ heuristics):
- Dot density analysis (`.........` leaders)
- Trailing page numbers
- Line length consistency
- Capitalization patterns
- Exception: Preserves financial/policy tables ($ symbols, data keywords)

## Command Reference

```bash
# Full loading
python load_pdf_qdrant.py                    # Standard (no context)
python load_pdf_qdrant.py --contextual       # With 3-tier context (recommended)
python load_pdf_qdrant.py --test             # Test mode (3 PDFs)
python load_pdf_qdrant.py --max-pdfs 10      # Limit PDFs
python load_pdf_qdrant.py --no-clear         # Append to existing

# Surgical reload
python reload_single_pdf.py <filename>       # Reload single PDF

# Verification
python verify_qdrant.py                      # Verify collection
```

### Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--test` | Process only 3 PDFs |
| `--max-pdfs N` | Maximum PDFs to process |
| `--no-clear` | Don't clear collection before loading |
| `--contextual` | Enable 3-tier context generation |
| `--no-contextual` | Disable context (override config) |

## Configuration

**File:** `LOAD_DB/config.py`

### Qdrant
```python
QDRANT_COLLECTION_NAME = 'tro-child-hybrid-v1'
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
```

### Embeddings
```python
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536
BM25_VOCABULARY_SIZE = 30000
```

### Chunking
```python
CHUNK_SIZE = 1000          # Characters per chunk
CHUNK_OVERLAP = 200        # Character overlap
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
```

### Contextual Processing
```python
GROQ_MODEL = 'openai/gpt-oss-20b'
ENABLE_CONTEXTUAL_RETRIEVAL = True
USE_PREVIOUS_CHUNK_CONTEXT = True
CONTEXT_BATCH_SIZE = 10
CONTEXT_RATE_LIMIT_DELAY = 2  # seconds
```

### Table PDFs
```python
TABLE_PDFS = [
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
    'bcy-26-psoc-chart-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf',
]
```

## Directory Structure

```
LOAD_DB/
├── config.py                    # Configuration
├── load_pdf_qdrant.py           # Main loading script
├── reload_single_pdf.py         # Surgical reload utility
├── contextual_processor.py      # 3-tier context generation
├── text_cleaner.py              # Text cleaning utilities
├── sparse_embedder.py           # BM25 sparse embedding
├── verify_qdrant.py             # Collection verification
├── extractors/
│   ├── __init__.py              # Extractor factory
│   ├── pymupdf_extractor.py     # Fast extraction
│   └── docling_extractor.py     # Table extraction
├── shared/
│   ├── pdf_processor.py         # Document cleaning, filtering
│   └── qdrant_uploader.py       # Hybrid upload with context
├── prompts/
│   ├── master_context_prompt.py # Tier 1 context
│   ├── document_context_prompt.py # Tier 2 prompt
│   └── chunk_context_prompt.py  # Tier 3 prompt
├── checkpoints/                 # Progress + cached contexts
├── logs/                        # Processing logs
└── reports/                     # Loading reports
```

## Outputs

### Checkpoints
- `checkpoint_{timestamp}.json` - Progress (every 5 PDFs)
- `doc_context_{pdf_id}.json` - Cached document contexts

### Logs
- `pdf_load_{timestamp}.log` - Processing details

### Reports
- `load_report_{timestamp}.txt` - Summary statistics
- `filtered_chunks_{timestamp}.txt` - Filtered TOC chunks (if any)

## Performance

### Standard Mode
- Speed: ~2.5 minutes for 42 PDFs
- Output: ~3,700 chunks

### Contextual Mode
- Speed: ~60 minutes for 42 PDFs
- Context generation: ~$2.00 (GROQ)
- Embedding cost: ~$0.03 (OpenAI)

### Surgical Reload
- Speed: ~2 minutes for 1 PDF
- 40x faster than full reload

## Troubleshooting

### "Collection already exists"
Default behavior clears collection. Use `--no-clear` to append.

### Context generation fails
Check GROQ API key. Contexts are cached, so restart continues from last cached PDF.

### TOC chunks not filtered
Check `text_cleaner.is_likely_toc()` - may need tuning for new PDF formats.
