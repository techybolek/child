# Hybrid Search Implementation: Complete

**Date:** 2025-11-20
**Status:** Phase 3 COMPLETE ✅
**Next:** Phase 4 (Hybrid Retriever)

---

## Executive Summary

Successfully implemented **hybrid search** combining dense semantic vectors (OpenAI embeddings) with sparse keyword vectors (BM25) in a single Qdrant collection. All 3 test PDFs loaded successfully with 303 total chunks.

**Key Achievement:** Fixed critical Qdrant collection creation API issue - sparse vectors require separate `sparse_vectors_config` parameter with `SparseVectorParams()`, not inclusion in `vectors_config`.

---

## Architecture Overview

### Single Collection, Dual Vectors

**Collection:** `tro-child-hybrid-v1`

**Named Vector Structure:**
```python
vector_data = {
    "dense": [1536-dim float list],      # OpenAI text-embedding-3-small
    "sparse": SparseVector(              # BM25 term frequencies
        indices=[int list],              # Hashed token indices (sorted)
        values=[float list]              # Term frequency values
    )
}
```

**Collection Configuration:**
```python
# Correct API structure
client.create_collection(
    collection_name="tro-child-hybrid-v1",
    vectors_config={
        "dense": VectorParams(
            size=1536,
            distance=Distance.COSINE
        )
    },
    sparse_vectors_config={              # Separate parameter
        "sparse": SparseVectorParams()   # No size/distance params
    }
)
```

---

## Implementation Details

### Phase 3.1: BM25 Sparse Embedder

**File:** `LOAD_DB/sparse_embedder.py`

**Key Features:**
- Tokenization with special pattern preservation (dollar amounts, percentages, acronyms)
- Hash-based vocabulary (30,000 size) with collision handling
- Sorted, unique indices (Qdrant requirement)
- Term frequency scoring

**Example:**
```python
embedder = BM25Embedder(vocab_size=30000)
sparse_vec = embedder.embed_query("Family of 5 earns $4,106")
# Returns: SparseVector(indices=[274, 276, 1051, ...], values=[1.0, 2.0, 1.0, ...])
```

### Phase 3.2: Hybrid Upload Support

**File:** `LOAD_DB/shared/qdrant_uploader.py`

**Changes:**
- Added `hybrid_mode` parameter to `upload_with_embeddings()`
- Generate sparse vectors from **original content** (not enriched context)
- Create named vector dict with both dense + sparse
- Dense uses contextual embeddings (3-tier), sparse uses original text

**Rationale for Original Content in Sparse:**
- Preserves exact keyword matching
- Avoids contextual "noise" in term frequencies
- Complements dense semantic search

### Phase 3.3: Collection Management

**File:** `LOAD_DB/load_pdf_qdrant.py`

**Changes:**
1. Added `hybrid_mode` parameter to `__init__`
2. Collection name routing: `tro-child-hybrid-v1` for hybrid mode
3. Fixed `clear_and_recreate_collection()` - use `sparse_vectors_config`
4. Fixed `ensure_collection_exists()` - use `sparse_vectors_config`
5. Added `--hybrid` CLI flag
6. Import `SparseVectorParams` from `qdrant_client.models`

**CLI Usage:**
```bash
# Standard (dense only)
python load_pdf_qdrant.py --contextual

# Hybrid (dense + sparse)
python load_pdf_qdrant.py --hybrid --contextual

# Test mode
python load_pdf_qdrant.py --test --hybrid --contextual
```

---

## Critical Bug Fix: Collection Creation API

### The Problem

**Incorrect Implementation:**
```python
# WRONG: Sparse in vectors_config with VectorParams
vectors_config = {
    "dense": VectorParams(size=1536, distance=COSINE),
    "sparse": VectorParams(size=30000, distance=DOT)  # ❌ Wrong class
}

client.create_collection(
    collection_name=name,
    vectors_config=vectors_config  # ❌ Sparse included here
)
```

**Error:** `400 Bad Request: "Conversion between sparse and regular vectors failed"`

### The Solution

**Correct Implementation:**
```python
# CORRECT: Separate sparse_vectors_config with SparseVectorParams
client.create_collection(
    collection_name=name,
    vectors_config={
        "dense": VectorParams(size=1536, distance=COSINE)
    },
    sparse_vectors_config={              # ✅ Separate parameter
        "sparse": SparseVectorParams()   # ✅ No size/distance
    }
)
```

**Key Insight:** Qdrant API requires **asymmetric configuration**:
- Dense: `vectors_config` with `VectorParams(size, distance)`
- Sparse: `sparse_vectors_config` with `SparseVectorParams()` (no params)

---

## Testing Results

### Phase 3.6: Test Mode (3 PDFs)

**Command:**
```bash
python load_pdf_qdrant.py --test --hybrid --contextual
```

**Results:**
```
Collection: tro-child-hybrid-v1
- PDF 1: trs-parent-brochure.pdf (4 chunks)
- PDF 2: early-childhood-system-needs-assessment-in-texas-final-accessible.pdf (287 chunks)
- PDF 3: child-care-stakeholder-input-policy-twc.pdf (12 chunks)

Total: 303 chunks uploaded
Failures: 0
Duration: ~5 minutes
```

**Collection Verification:**
```python
info = client.get_collection('tro-child-hybrid-v1')

# Vectors config (dense)
info.config.params.vectors == {
    'dense': VectorParams(size=1536, distance=COSINE)
}

# Sparse vectors config (sparse)
info.config.params.sparse_vectors == {
    'sparse': SparseVectorParams()
}
```

✅ **All tests passed!**

---

## Technical Specifications

### Dense Vectors

- **Model:** OpenAI `text-embedding-3-small`
- **Dimension:** 1536
- **Distance:** COSINE
- **Content:** Contextual embeddings (Master + Document + Chunk contexts + Original)
- **Purpose:** Semantic similarity search

### Sparse Vectors

- **Method:** BM25 term frequency
- **Vocabulary:** 30,000 (hash-based)
- **Content:** Original chunk text (no context)
- **Format:** `SparseVector(indices=[sorted ints], values=[floats])`
- **Purpose:** Exact keyword matching

### Point Structure

```python
PointStruct(
    id=1,
    vector={
        "dense": [0.123, 0.456, ...],  # 1536 floats
        "sparse": SparseVector(
            indices=[16, 825, 942, ...],  # Sorted unique ints
            values=[1.0, 2.0, 1.0, ...]   # Term frequencies
        )
    },
    payload={
        "text": "original chunk content",
        "filename": "document.pdf",
        "page": 5,
        "has_context": True,
        "master_context": "...",
        "document_context": "...",
        "chunk_context": "...",
        # ... other metadata
    }
)
```

---

## Files Modified

### 1. `LOAD_DB/sparse_embedder.py` (NEW)
- BM25 sparse vector embedder
- Tokenization with special patterns
- Hash-based vocabulary with collision handling
- 207 lines

### 2. `LOAD_DB/shared/qdrant_uploader.py`
- Added `hybrid_mode` parameter
- Generate sparse vectors from original content
- Create named vector dict
- Lines modified: ~30

### 3. `LOAD_DB/load_pdf_qdrant.py`
- Added `hybrid_mode` parameter
- Fixed collection creation API (2 methods)
- Added `--hybrid` CLI flag
- Collection name routing
- Lines modified: ~40
- **Key fix:** Import `SparseVectorParams`, use `sparse_vectors_config` parameter

### 4. `LOAD_DB/config.py`
- Added `BM25_VOCABULARY_SIZE = 30000`
- Added `SPARSE_ON_DISK = True`

---

## Debugging Journey

### Timeline

1. **Initial Implementation** - All code complete (Phases 3.1-3.5)
2. **Testing** - Collection created but point upload failed
3. **Error 1:** "Conversion between sparse and regular vectors failed" (first PDF)
4. **Error 2:** "indices: must be unique" (subsequent PDFs)
5. **Investigation:** Isolated tests all passed (BM25, minimal points)
6. **Root Cause:** Collection configured with wrong API structure
7. **Solution:** Delete collection, recreate with correct API
8. **Verification:** All 3 test PDFs uploaded successfully

### Key Lessons

1. **Test collection creation first** with minimal case before full implementation
2. **Qdrant API asymmetry** not intuitive but clearly documented
3. **Separate concerns:** Dense and sparse use different configuration structures
4. **Verify collection config** after creation before assuming point format is wrong

---

## Configuration Reference

### Environment Variables

```bash
# Required for all modes
export QDRANT_API_URL="your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"
export OPENAI_API_KEY="your-openai-key"
export GROQ_API_KEY="your-groq-key"  # For contextual mode
```

### Config Settings

**`LOAD_DB/config.py`:**
```python
# Qdrant collections
QDRANT_COLLECTION_NAME = 'tro-child-1'              # Standard
QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-2'  # Contextual
QDRANT_COLLECTION_NAME_HYBRID = 'tro-child-hybrid-v1'  # Hybrid

# Embeddings
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536

# BM25 (for hybrid mode)
BM25_VOCABULARY_SIZE = 30000
SPARSE_ON_DISK = True

# Chunking
CHUNK_SIZE = 1000        # Characters
CHUNK_OVERLAP = 200      # Characters

# Upload
UPLOAD_BATCH_SIZE = 100
```

---

## Next Steps

### Phase 4: Hybrid Retriever (3-4 hours)

**Goal:** Query both dense and sparse vectors, fuse results with RRF

**Files to create/modify:**
1. `chatbot/hybrid_retriever.py` - RRF fusion via Qdrant Query API
2. `chatbot/config.py` - Add hybrid settings
3. `chatbot/handlers/rag_handler.py` - Support hybrid retrieval

**Qdrant Query API:**
```python
results = client.query_points(
    collection_name="tro-child-hybrid-v1",
    prefetch=[
        Prefetch(query=dense_vector, using="dense", limit=100),
        Prefetch(query=sparse_vector, using="sparse", limit=100)
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=20
)
```

### Phase 5: Testing & Evaluation (2-3 hours)

1. Load full dataset with `--hybrid --contextual`
2. Run evaluation comparison (baseline vs hybrid)
3. Verify BCY-26 failure case is fixed
4. Document results

---

## References

### Qdrant Documentation (2025)

- **Hybrid Search Guide:** https://qdrant.tech/documentation/beginner-tutorials/hybrid-search-fastembed/
- **Hybrid Queries:** https://qdrant.tech/documentation/concepts/hybrid-queries/
- **Collection Creation:** https://qdrant.tech/documentation/concepts/collections/

### Related Documents

- `SPECS/PLANS/hybrid_search_implementation.md` - Original plan
- `SPECS/DOC/hybrid_search_blocker_resolution.md` - API bug fix details
- `SPECS/loading_pipeline.md` - Loading pipeline architecture
- `SPECS/evaluation_system.md` - Evaluation methodology

---

## Summary

✅ **Phase 3 Complete** - Hybrid search infrastructure ready
✅ **303 chunks** uploaded to `tro-child-hybrid-v1`
✅ **0 failures** in test mode
✅ **API fix** documented for future reference

**Ready for Phase 4:** Implement hybrid retriever with RRF fusion for production queries.

---

**Document Version:** 1.0
**Author:** Claude (Sonnet 4.5)
**Date:** 2025-11-20
**Status:** Implementation Complete, Testing Passed
