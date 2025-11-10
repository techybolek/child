# Contextual Embedding Implementation Guide

## Overview

Three-tier hierarchical context generation system that improves RAG retrieval by enriching chunk embeddings with semantic metadata. Contexts are used **only for embedding computation**, keeping retrieved content clean and user-facing.

## Architecture: Three-Tier Context Hierarchy

```
Master Context (Tier 1)
    ↓ [static, reused for all PDFs]
Document Context (Tier 2)
    ↓ [generated once per PDF from first 2000 chars]
Chunk Context (Tier 3)
    ↓ [generated per chunk using document context]
```

### Tier 1: Master Context (Static)
- **Source**: `LOAD_DB/prompts/master_context_prompt.py`
- **Content**: Domain identifier (~50 tokens)
- **Reuse**: Same for all PDFs
- **Example**: "This is official Texas Workforce Commission (TWC) documentation regarding childcare assistance programs..."

### Tier 2: Document Context (Per-PDF)
- **Source**: `LOAD_DB/prompts/document_context_prompt.py`
- **Generated**: Once per PDF from first 2000 characters
- **Cached**: `LOAD_DB/checkpoints/doc_context_{pdf_id}.json`
- **Content**: Succinct 2-3 sentence summary (~200-400 tokens)
- **Prompt style**: Simple, condensed prompt requesting brief context (pragmatic approach for maintainability)
- **Example**: "The Texas Workforce Commission's Child Care Services Guide provides comprehensive guidance on the administration of childcare assistance programs in Texas, including the Child Care Development Fund (CCDF) and Provider Services Operational Consultation (PSOC)."

### Tier 3: Chunk Context (Per-Chunk)
- **Source**: `LOAD_DB/prompts/chunk_context_prompt.py`
- **Generated**: Per chunk in batches via GROQ API
- **Content**: Brief positional context (~50-100 tokens)
- **Prompt inputs**: `document_context` (Tier 2) + `chunk_text` (original content)
- **Batching**: 10 chunks per batch with 2-second rate limiting

## Embedding & Storage Strategy

**Key Design**: Contexts enrich embeddings but don't pollute retrieved content.

```
EMBEDDING INPUT (used for vector computation):
  [Master Context] + [Document Context] + [Chunk Context] + [Original Content]
  ↓
  OpenAI text-embedding-3-small → 1536-dimensional vector

STORAGE IN QDRANT (what users retrieve):
  page_content: [Original Content Only] ✓ CLEAN
  metadata.master_context: [Master Context]
  metadata.document_context: [Document Context]
  metadata.chunk_context: [Chunk Context]
  metadata.has_context: True
  vector: [enriched embedding computed above]
```

## Implementation Components

### Files Created
- `LOAD_DB/prompts/__init__.py` - Module exports
- `LOAD_DB/prompts/master_context_prompt.py` - Tier 1 constant
- `LOAD_DB/prompts/document_context_prompt.py` - Tier 2 prompt builder
- `LOAD_DB/prompts/chunk_context_prompt.py` - Tier 3 prompt builder
- `LOAD_DB/contextual_processor.py` - GROQ API integration using `requests` library (~300 lines)
- `LOAD_DB/text_cleaner.py` - Text cleaning and TOC/metadata chunk filtering

### Files Modified
- `LOAD_DB/config.py` - Added contextual settings:
  - `GROQ_MODEL = 'openai/gpt-oss-20b'`
  - `QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1-contextual'`
  - `CONTEXT_BATCH_SIZE = 10`
  - `CONTEXT_RATE_LIMIT_DELAY = 2` (seconds)
  - `ENABLE_CONTEXTUAL_RETRIEVAL = True`

- `LOAD_DB/load_pdf_qdrant.py` - Integration:
  - `--contextual` command-line flag
  - Text cleaning (page numbers, whitespace normalization)
  - TOC/metadata chunk filtering (heuristic-based detection)
  - Document context generation in `process_pdf()`
  - Chunk context generation in `upload_documents_to_qdrant()`
  - Enriched embedding with separate metadata storage

- `LOAD_DB/test_single_pdf.py` - Test helper:
  - Loads single PDF with contextual mode
  - Limits to 10 chunks for fast testing
  - Auto-cleans cached document context before run
  - Collection: `tro-child-1-contextual` (separate from original)

## Text Cleaning & TOC Filtering

**Module**: `LOAD_DB/text_cleaner.py`

The text cleaner preprocesses PDF content to improve embedding quality:

### Features
1. **Text Cleaning** (`clean_text()`)
   - Removes page numbers and footers
   - Normalizes whitespace
   - Preserves semantic content

2. **TOC Detection** (`is_likely_toc()`)
   - Identifies table-of-contents chunks using heuristics:
     - High dot density (TOC leader dots)
     - Lines ending with page numbers
     - Consistent line lengths
     - Short total content length
   - Filters these chunks before context generation

3. **Data Table Preservation** (`is_likely_data_table()`)
   - Detects and preserves important data tables (income limits, payment rates, eligibility thresholds)
   - Ensures critical metrics remain in retrievable content

### Integration
- Applied in `load_pdf_qdrant.py` to all PDF pages during loading
- Chunks filtered before document context generation (avoids generating contexts for metadata)
- Reports: `LOAD_DB/reports/filtered_chunks_*.txt` with statistics

### Impact
- Reduces noise in embeddings (removes page numbers, TOC entries)
- Decreases tokens required for context generation (fewer chunks to process)
- Improves retrieval relevance by prioritizing substantive content

## Quick Start: Test-Load Single PDF

### Automatic Test-Load (Recommended)
```bash
cd /home/tromanow/COHORT/TX/LOAD_DB

# Load single PDF with 10 chunks (quick test)
python test_single_pdf.py

# Output:
# ✓ Cleaned cache: deleted doc_context_child-care-services-guide-twc.json
# ✓ Extracted 402 pages from PDF
# ✓ Limited to first 10 chunks for testing
# ✓ Uploaded 10 chunks to Qdrant
# Ready for testing...
```

### Manual Full Load (All PDFs)
```bash
cd /home/tromanow/COHORT/TX/LOAD_DB

# Load all 37 PDFs with contexts
python load_pdf_qdrant.py --contextual

# Uses: tro-child-1-contextual collection
# Time: ~30-45 minutes
# Output: 740+ chunks with enriched embeddings
```

### Load Specific PDF Count (Testing)
```bash
# Load first 3 PDFs only
python load_pdf_qdrant.py --test --contextual

# Clears tro-child-1-contextual collection and reloads
```

## Collections

- **Original**: `tro-child-1` (no contextual metadata)
- **Contextual**: `tro-child-1-contextual` (with three-tier contexts)

Test with specific collection:
```bash
# Resume failed evaluation with contextual collection
python -m evaluation.run_evaluation --resume --resume-limit 1 --collection tro-child-1-contextual
```

## Verification

After test-load, verify data structure:
```python
from qdrant_client import QdrantClient

client = QdrantClient(url=os.getenv('QDRANT_API_URL'),
                      api_key=os.getenv('QDRANT_API_KEY'))
points = client.scroll('tro-child-1-contextual', limit=5)[0]

for point in points:
    assert point.payload.get('has_context') == True
    assert len(point.payload.get('text', '')) > 0  # Original content only
    assert 'master_context' in point.payload
    assert 'document_context' in point.payload
    assert 'chunk_context' in point.payload
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Document Context Gen | ~0.5-1 sec per PDF |
| Chunk Context Gen | ~0.4-0.5 sec per chunk |
| Rate Limiting | 2 sec between batches |
| Batch Size | 10 chunks |
| Master Context | ~50 tokens (reused) |
| Document Context | ~200-400 tokens (simplified prompt) |
| Chunk Context | ~50-100 tokens |
| Total Enrichment | ~300-550 tokens per chunk |
| Embedding Model | text-embedding-3-small (1536 dims) |
| TOC Filtering | ~10-20% chunk reduction |

## Caching

Document contexts cached to avoid regeneration:
- **Location**: `LOAD_DB/checkpoints/doc_context_{pdf_id}.json`
- **Cache Hit**: Reuses cached context (instant)
- **Cache Miss**: Regenerates via GROQ API (~0.5-1 sec)
- **Clear Cache**: `test_single_pdf.py` auto-cleans on each run

## Error Handling

- **Rate Limiting (429)**: Exponential backoff (2s, 4s, 8s)
- **Server Errors (5xx)**: Retry up to 3 times
- **Timeout**: 30-second timeout per request
- **Failed Context**: Logs warning, proceeds without context for that chunk
- **Graceful Degradation**: If document context fails, chunk context not generated

## Testing Strategy

1. **Quick Test** (2-3 min):
   ```bash
   python test_single_pdf.py  # 10 chunks, 1 PDF
   ```

2. **Small Scale Test** (3-5 min):
   ```bash
   python load_pdf_qdrant.py --test --contextual  # 3 PDFs
   ```

3. **Full Scale Test** (30-45 min):
   ```bash
   python load_pdf_qdrant.py --contextual  # 37 PDFs, no --clear deletes old collection
   ```

4. **Validation**:
   ```bash
   # Resume failed evaluation with contextual collection
   python -m evaluation.run_evaluation --resume --resume-limit 1 --collection tro-child-1-contextual
   ```

## Success Criteria

✅ Document contexts generated (2-3 sentences with key programs/audience)
✅ Chunk contexts generated in batches with rate limiting
✅ Contexts stored in metadata (not in page_content)
✅ Embeddings computed from enriched text (all three tiers combined)
✅ Original content clean when retrieved (no context pollution)
✅ Text cleaning removes page numbers and noise
✅ TOC filtering removes ~10-20% of chunks (metadata reduction)
✅ Caching works (instant re-runs with `test_single_pdf.py`)
✅ Document context caching reduces GROQ API calls
✅ Failing test case retrieves correct answer using contextual collection

## Implementation Notes

### Design Choices

**Simplified Prompts (Pragmatic Approach)**
- Document and chunk context prompts are intentionally simplified for maintainability
- Instead of structured 5-point guidance, prompts request 2-3 sentence summaries
- Simplification reduces prompt engineering overhead while maintaining effectiveness
- Trade-off: Shorter contexts (~200-400 tokens) vs. structured outputs

**Requests Library Instead of GROQ SDK**
- Uses `requests` library for direct HTTP calls instead of official GROQ Python SDK
- Provides better control over timeouts, retries, and error handling
- Eliminates additional dependency
- Functionally equivalent to SDK but with more transparency

**Text Cleaning & TOC Filtering**
- Not originally planned, but found to significantly improve embedding quality
- Removes ~10-20% of chunks (mostly metadata and TOC pages)
- Reduces GROQ API calls required for context generation
- Preserves critical data tables (income limits, thresholds)

### Caching Strategy

Document context caching is critical for efficiency:
- 38 PDFs successfully cached across runs
- Cache hits are instant (no API calls)
- Cache misses trigger GROQ API (~0.5-1 sec)
- Test mode (`test_single_pdf.py`) auto-clears cache for fresh generation

### API Client Details

The GROQ API client in `contextual_processor.py`:
- Base URL: `https://api.groq.com/openai/v1`
- Uses OpenAI-compatible API format
- Implements exponential backoff: 2s, 4s, 8s for rate limits
- 30-second request timeout
- Max 3 retries for transient failures

## Related Files

- Implementation plan: `SPECS/contextual_retrieval_implementation.md`
- Chatbot config: `chatbot/config.py` (GROQ model settings)
- Original loader: `LOAD_DB/load_pdf_qdrant.py` (before contextual mode)
