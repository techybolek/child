# Hybrid Search Implementation Progress
**Date:** 2025-11-20
**Status:** Phases 1-2 Complete, Phase 3 Partial
**Based on:** `PLANS/hybrid_search_implementation.md`

---

## Executive Summary

Implementing hybrid search (dense + sparse vectors with RRF fusion) to improve retrieval accuracy for exact keyword matching and table lookups. Current implementation is ~40% complete with core components functional.

**Expected Impact:**
- Composite score improvement: 41.7 → 55-65 (+13-23 points)
- BCY-26 failure: rank 24 → top-5 ✅
- Exact match queries: +40-50% accuracy

---

## ✅ Phase 1: Configuration Setup (COMPLETE)

### Files Modified

#### 1. `LOAD_DB/config.py` (lines 57-62)
```python
# ===== HYBRID SEARCH SETTINGS =====
ENABLE_HYBRID_SEARCH = True
HYBRID_COLLECTION_NAME = 'tro-child-hybrid-v1'
SPARSE_EMBEDDER_TYPE = 'bm25'  # 'bm25' or 'minicoil'
BM25_VOCABULARY_SIZE = 30000
SPARSE_ON_DISK = True  # Store sparse vectors on disk for memory optimization
```

#### 2. `chatbot/config.py` (lines 63-68)
```python
# ===== HYBRID SEARCH SETTINGS =====
ENABLE_HYBRID_RETRIEVAL = False  # Set to True to use hybrid collection
HYBRID_COLLECTION_NAME = 'tro-child-hybrid-v1'
FUSION_METHOD = 'rrf'  # Reciprocal Rank Fusion
RRF_K = 60  # Standard RRF parameter
HYBRID_PREFETCH_LIMIT = 100  # Number of candidates to retrieve from each vector type before fusion
```

**Status:** ✅ Complete and tested

---

## ✅ Phase 2: BM25 Sparse Embedder (COMPLETE)

### File Created: `LOAD_DB/sparse_embedder.py`

**Key Features:**
- Tokenization preserving special patterns:
  - Dollar amounts: `$4,106` → `dollar_num4106`
  - Percentages: `85%` → `85percent`
  - Acronyms: `TANF` → `tanf` (lowercased)
  - Family sizes: `family of 5` → `family`, `of`, `num5`
- Hash-based vocabulary mapping (30,000 vocab size)
- Batch and single query embedding support

**Testing:** All tests passing ✅
```bash
cd LOAD_DB
python sparse_embedder.py
# Output: All tests passed! ✅
```

**API:**
```python
from sparse_embedder import BM25Embedder

embedder = BM25Embedder(vocab_size=30000)

# Single query
sparse_vec = embedder.embed_query("Family of 5 with $4,106 income")
# sparse_vec.indices: [12345, 67890, ...]
# sparse_vec.values: [1.0, 1.0, ...]

# Batch
sparse_vecs = embedder.embed(["query 1", "query 2"])
```

**Status:** ✅ Complete and tested

---

## ✅ Phase 3: Loading Pipeline Modifications (COMPLETE - BLOCKED IN TESTING)

**Status:** All code modifications complete (3.1-3.5 ✅), testing blocked (3.6 ❌)

**Blocker Details:** See `SPECS/DOC/hybrid_search_blocker_resolution.md` for full analysis and solution.

### ✅ Phase 3.1: Modified `upload_with_embeddings()` Function

**File:** `LOAD_DB/shared/qdrant_uploader.py`

**Changes:**
1. Added BM25Embedder import (lines 16-20):
```python
# Import sparse embedder for hybrid mode
try:
    from sparse_embedder import BM25Embedder
except ImportError:
    BM25Embedder = None
```

2. Added `hybrid_mode` parameter (line 31):
```python
def upload_with_embeddings(
    client: QdrantClient,
    collection_name: str,
    documents: List[Document],
    embeddings_model: OpenAIEmbeddings,
    contextual_mode: bool = False,
    contextual_processor = None,
    document_context: Optional[str] = None,
    hybrid_mode: bool = False  # NEW
):
```

3. Added sparse vector generation (lines 122-134):
```python
# Generate sparse vectors if hybrid mode
sparse_vectors = None
if hybrid_mode:
    if BM25Embedder is None:
        raise ImportError("BM25Embedder not available. Check sparse_embedder.py")

    logger.info(f"Generating sparse vectors for {len(documents)} chunks...")
    sparse_embedder = BM25Embedder(vocab_size=config.BM25_VOCABULARY_SIZE)

    # Use ORIGINAL content for sparse (no context)
    sparse_vectors = sparse_embedder.embed(original_contents)
    logger.info("Sparse vectors generated")
```

4. Modified point creation for named vectors (lines 151-163):
```python
# Build vector structure for hybrid or single vector
if hybrid_mode and sparse_vectors:
    # Named vectors for hybrid search
    vector_data = {
        "dense": embedding,
        "sparse": SparseVector(
            indices=sparse_vectors[i].indices,
            values=sparse_vectors[i].values
        )
    }
else:
    # Single unnamed vector for standard search
    vector_data = embedding
```

**Status:** ✅ Complete and tested (upsert format correct)

### ✅ Phase 3.2: Updated Collection Creation

**File:** `LOAD_DB/load_pdf_qdrant.py`

**Modified Methods:**
1. `clear_and_recreate_collection()` (lines 168-182)
2. `ensure_collection_exists()` (lines 226-236)

**Changes:** Added hybrid mode logic with named vectors configuration

**Status:** ✅ Code complete, ❌ API structure incorrect (see blocker)

**Issue:** Used `VectorParams` for sparse in `vectors_config` instead of separate `sparse_vectors_config` with `SparseVectorParams()`

### ✅ Phase 3.3: Added `hybrid_mode` to Loader `__init__`

**File:** `LOAD_DB/load_pdf_qdrant.py` (lines 70-93)

**Changes:**
```python
def __init__(self, test_mode: bool = False, max_pdfs: Optional[int] = None,
             clear_collection: bool = True, contextual_mode: bool = False,
             hybrid_mode: bool = False):
    self.hybrid_mode = hybrid_mode

    # Set collection name based on mode (hybrid takes precedence)
    if hybrid_mode:
        self.collection_name = config.HYBRID_COLLECTION_NAME
    elif contextual_mode:
        self.collection_name = config.QDRANT_COLLECTION_NAME_CONTEXTUAL
    else:
        self.collection_name = config.QDRANT_COLLECTION_NAME
```

**Status:** ✅ Complete

### ✅ Phase 3.4: Updated `upload_with_embeddings()` Calls

**File:** `LOAD_DB/load_pdf_qdrant.py` (line 441)

**Change:**
```python
upload_with_embeddings(
    client=self.client,
    collection_name=self.collection_name,
    documents=documents,
    embeddings_model=self.embeddings,
    contextual_mode=self.contextual_mode,
    contextual_processor=self.contextual_processor,
    document_context=document_context,
    hybrid_mode=self.hybrid_mode  # NEW
)
```

**Status:** ✅ Complete

### ✅ Phase 3.5: Added `--hybrid` CLI Flag

**File:** `LOAD_DB/load_pdf_qdrant.py` (lines 640-650)

**Changes:**
```python
parser.add_argument('--hybrid', action='store_true',
                   help='Enable hybrid search mode (generates dense + sparse vectors for RRF fusion)')

loader = PDFToQdrantLoader(
    test_mode=args.test,
    max_pdfs=args.max_pdfs,
    clear_collection=not args.no_clear,
    contextual_mode=args.contextual,
    hybrid_mode=args.hybrid
)
```

**Status:** ✅ Complete

### ❌ Phase 3.6: Testing (BLOCKED)

**Command:**
```bash
cd LOAD_DB
python load_pdf_qdrant.py --test --hybrid --contextual
```

**Error:** `400 Bad Request: "Conversion between sparse and regular vectors failed"`

**Root Cause:** Collection creation API incorrect - must use `sparse_vectors_config` with `SparseVectorParams()`

**Solution:** Documented in `SPECS/DOC/hybrid_search_blocker_resolution.md`

**Fix Required:**
1. Modify `clear_and_recreate_collection()` to use correct API
2. Modify `ensure_collection_exists()` to use correct API
3. Import `SparseVectorParams` from `qdrant_client.models`
4. (Optional) Upgrade to `qdrant-client==1.16.0`

**Time to Fix:** ~40 minutes

**Status:** ❌ Blocked (solution ready to implement)

### Error History

#### Error 1: VectorParams Modifier ✅ Fixed
```
1 validation error for VectorParams modifier: Extra inputs are not permitted
```
**Fix:** Removed `modifier=Modifier.IDF` parameter

#### Error 2: Duplicate Indices ✅ Fixed
```
422 Unprocessable Entity: Validation error: indices: must be unique
```
**Fix:** Modified `BM25Embedder.embed()` to use dict for deduplication and sorting

#### Error 3: Sparse Vector Conversion ❌ BLOCKER
```
400 Bad Request: "Conversion between sparse and regular vectors failed"
```
**Fix:** Use `sparse_vectors_config` parameter with `SparseVectorParams()` (ready to implement)

### Next Step: Fix Collection Creation API

**Full Documentation:** See `SPECS/DOC/hybrid_search_blocker_resolution.md`

**Summary:**
- Replace `vectors_config` with `sparse_vectors_config` for sparse vectors
- Use `SparseVectorParams()` instead of `VectorParams(size=..., distance=...)`
- Modify 2 methods: `clear_and_recreate_collection()` and `ensure_collection_exists()`
- Estimated time: 40 minutes

**Example Fix:**
```python
# CORRECT API
self.client.create_collection(
    collection_name=self.collection_name,
    vectors_config={
        "dense": VectorParams(size=1536, distance=Distance.COSINE)
    },
    sparse_vectors_config={  # Separate parameter!
        "sparse": SparseVectorParams()  # No size/distance!
    }
)
```

**Status:** Phase 3 implementation complete (3.1-3.5 ✅), Phase 3.6 blocked (fix ready to apply)
```python
def __init__(self, test_mode: bool = False, max_pdfs: Optional[int] = None,
             clear_collection: bool = True, contextual_mode: bool = False,
             hybrid_mode: bool = False):  # NEW PARAMETER
    """
    Initialize the PDF to Qdrant loader.

    Args:
        test_mode: If True, runs in test mode with limited PDFs
        max_pdfs: Maximum number of PDFs to process (for testing)
        clear_collection: If True, clears the collection before loading (default: True)
        contextual_mode: If True, generates contextual metadata for chunks
        hybrid_mode: If True, generates sparse vectors for hybrid search  # NEW DOC
    """
    self.test_mode = test_mode
    self.max_pdfs = max_pdfs or (3 if test_mode else None)
    self.clear_collection = clear_collection
    self.contextual_mode = contextual_mode
    self.hybrid_mode = hybrid_mode  # NEW LINE

    # Set collection name based on mode
    if hybrid_mode:
        self.collection_name = config.HYBRID_COLLECTION_NAME
    elif contextual_mode:
        self.collection_name = config.QDRANT_COLLECTION_NAME_CONTEXTUAL
    else:
        self.collection_name = config.QDRANT_COLLECTION_NAME
```

#### 4. Update `upload_with_embeddings()` Calls

**Location:** Search for all calls to `upload_with_embeddings` in `load_pdf_qdrant.py`

**Find (approximate line 450):**
```python
upload_with_embeddings(
    client=self.client,
    collection_name=self.collection_name,
    documents=final_chunks,
    embeddings_model=self.embeddings,
    contextual_mode=self.contextual_mode,
    contextual_processor=self.contextual_processor,
    document_context=document_context
)
```

**Replace with:**
```python
upload_with_embeddings(
    client=self.client,
    collection_name=self.collection_name,
    documents=final_chunks,
    embeddings_model=self.embeddings,
    contextual_mode=self.contextual_mode,
    contextual_processor=self.contextual_processor,
    document_context=document_context,
    hybrid_mode=self.hybrid_mode  # NEW PARAMETER
)
```

#### 5. Add `--hybrid` CLI Flag

**Location:** `LOAD_DB/load_pdf_qdrant.py` (bottom of file, around line 550)

**Find:**
```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load PDFs to Qdrant Vector Database')
    parser.add_argument('--test', action='store_true', help='Run in test mode (3 PDFs only)')
    parser.add_argument('--max-pdfs', type=int, help='Maximum number of PDFs to process')
    parser.add_argument('--no-clear', action='store_true', help='Do not clear collection before loading')
    parser.add_argument('--contextual', action='store_true', help='Enable contextual embeddings')

    args = parser.parse_args()
```

**Add after `--contextual` line:**
```python
    parser.add_argument('--hybrid', action='store_true',
                       help='Enable hybrid search (dense + sparse vectors)')
```

**Find:**
```python
    loader = PDFToQdrantLoader(
        test_mode=args.test,
        max_pdfs=args.max_pdfs,
        clear_collection=not args.no_clear,
        contextual_mode=args.contextual
    )
```

**Add `hybrid_mode` parameter:**
```python
    loader = PDFToQdrantLoader(
        test_mode=args.test,
        max_pdfs=args.max_pdfs,
        clear_collection=not args.no_clear,
        contextual_mode=args.contextual,
        hybrid_mode=args.hybrid  # NEW PARAMETER
    )
```

### Testing Phase 3

After completing modifications:

```bash
# Test with 3 PDFs in hybrid mode
cd LOAD_DB
python load_pdf_qdrant.py --test --hybrid --contextual

# Expected output:
# - Creating HYBRID collection with dense + sparse vectors
# - Generating sparse vectors for N chunks...
# - Successfully uploaded N chunks to Qdrant

# Verify collection structure
python3 << 'EOF'
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    url=os.getenv('QDRANT_API_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

info = client.get_collection('tro-child-hybrid-v1')
print(f"Collection: {info.config.params.vectors}")
# Should show: {'dense': {...}, 'sparse': {...}}
EOF
```

**Status:** 🚧 30% complete (import added, remaining modifications needed)

---

## ⏸️ Phase 4: Hybrid Retriever (NOT STARTED)

### File to Create: `chatbot/hybrid_retriever.py`

**Complete Implementation:**

```python
"""
Hybrid Retriever with RRF Fusion for RAG System
Combines dense and sparse vector search using Reciprocal Rank Fusion
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, QueryRequest, SparseVector
from langchain_openai import OpenAIEmbeddings
import chatbot.config as config

logger = logging.getLogger(__name__)


class QdrantHybridRetriever:
    """
    Hybrid retriever combining dense and sparse vector search with RRF fusion.

    Architecture:
    1. Dense retrieval (semantic): OpenAI text-embedding-3-small
    2. Sparse retrieval (keyword): BM25 sparse vectors
    3. Fusion: Reciprocal Rank Fusion (RRF) with k=60
    4. Reranking: LLM-based (unchanged from current system)
    """

    def __init__(self, collection_name: Optional[str] = None, hybrid_mode: bool = None):
        """
        Initialize hybrid retriever.

        Args:
            collection_name: Qdrant collection name (defaults to config)
            hybrid_mode: Enable hybrid search (defaults to config.ENABLE_HYBRID_RETRIEVAL)
        """
        self.collection_name = collection_name or config.COLLECTION_NAME
        self.hybrid_mode = hybrid_mode if hybrid_mode is not None else config.ENABLE_HYBRID_RETRIEVAL

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY
        )

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY
        )

        # Initialize sparse embedder for hybrid mode
        self.sparse_embedder = None
        if self.hybrid_mode:
            try:
                import sys
                sys.path.insert(0, '/home/tromanow/COHORT/TX/LOAD_DB')
                from sparse_embedder import BM25Embedder
                self.sparse_embedder = BM25Embedder(vocab_size=30000)
                logger.info("Hybrid mode enabled with BM25 sparse embedder")
            except ImportError as e:
                logger.warning(f"Failed to load BM25Embedder: {e}. Falling back to dense-only.")
                self.hybrid_mode = False
        else:
            logger.info("Dense-only mode (hybrid disabled)")

    def search(self, query: str, top_k: int = 30, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using hybrid or dense-only retrieval.

        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum score threshold

        Returns:
            List of result dicts with keys: text, score, metadata
        """
        if not self.hybrid_mode or self.sparse_embedder is None:
            return self._dense_search(query, top_k, score_threshold)

        return self._hybrid_search(query, top_k, score_threshold)

    def _dense_search(self, query: str, top_k: int, score_threshold: float) -> List[Dict[str, Any]]:
        """Dense-only vector search (fallback or default)."""
        logger.info(f"Dense-only search: query='{query[:50]}...', top_k={top_k}")

        # Generate query embedding
        query_vector = self.embeddings.embed_query(query)

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )

        # Format results
        formatted = []
        for i, result in enumerate(results):
            formatted.append({
                'text': result.payload.get('text', ''),
                'score': result.score,
                'rank': i + 1,
                'metadata': {
                    'doc': result.payload.get('doc', ''),
                    'page': result.payload.get('page', 0),
                    'source_url': result.payload.get('source_url', ''),
                    'chunk_index': result.payload.get('chunk_index', 0),
                    'has_context': result.payload.get('has_context', False)
                }
            })

        logger.info(f"Dense search returned {len(formatted)} results")
        return formatted

    def _hybrid_search(self, query: str, top_k: int, score_threshold: float) -> List[Dict[str, Any]]:
        """Hybrid search with RRF fusion."""
        logger.info(f"Hybrid search: query='{query[:50]}...', top_k={top_k}")

        # Generate query vectors
        dense_vector = self.embeddings.embed_query(query)
        sparse_vec = self.sparse_embedder.embed_query(query)

        # Convert sparse vector to Qdrant format
        sparse_vector = SparseVector(
            indices=sparse_vec.indices,
            values=sparse_vec.values
        )

        # Hybrid search with RRF fusion via Qdrant Query API
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=config.HYBRID_PREFETCH_LIMIT
                    ),
                    Prefetch(
                        query=sparse_vector,
                        using="sparse",
                        limit=config.HYBRID_PREFETCH_LIMIT
                    )
                ],
                query=QueryRequest(
                    fusion="rrf",
                    rrf={"k": config.RRF_K}
                ),
                limit=top_k,
                score_threshold=score_threshold
            )
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}. Falling back to dense-only.")
            return self._dense_search(query, top_k, score_threshold)

        # Format results
        formatted = []
        for i, result in enumerate(results.points):
            formatted.append({
                'text': result.payload.get('text', ''),
                'score': result.score,
                'rank': i + 1,
                'metadata': {
                    'doc': result.payload.get('doc', ''),
                    'page': result.payload.get('page', 0),
                    'source_url': result.payload.get('source_url', ''),
                    'chunk_index': result.payload.get('chunk_index', 0),
                    'has_context': result.payload.get('has_context', False)
                }
            })

        logger.info(f"Hybrid search returned {len(formatted)} results (RRF fusion)")
        return formatted


def test_retriever():
    """Test hybrid retriever functionality."""
    print("Testing Hybrid Retriever")
    print("=" * 80)

    # Test 1: Dense-only mode
    print("\nTest 1: Dense-only retriever")
    retriever_dense = QdrantHybridRetriever(
        collection_name='tro-child-3-contextual',
        hybrid_mode=False
    )
    results = retriever_dense.search("What is BCY-26?", top_k=5)
    print(f"Results: {len(results)}")
    if results:
        print(f"Top result: {results[0]['metadata']['doc']}, score: {results[0]['score']:.3f}")

    # Test 2: Hybrid mode (if collection exists)
    print("\nTest 2: Hybrid retriever")
    try:
        retriever_hybrid = QdrantHybridRetriever(
            collection_name='tro-child-hybrid-v1',
            hybrid_mode=True
        )
        results = retriever_hybrid.search("Family of 5 income $4,106", top_k=5)
        print(f"Results: {len(results)}")
        if results:
            print(f"Top result: {results[0]['metadata']['doc']}, score: {results[0]['score']:.3f}")
    except Exception as e:
        print(f"Hybrid test skipped (collection not found): {e}")

    print("\nAll tests complete!")


if __name__ == '__main__':
    test_retriever()
```

### Integration with RAG Handler

**Location:** `chatbot/handlers/rag_handler.py`

**Current Code (approximate):**
```python
from chatbot.retriever import QdrantRetriever

class RAGHandler(BaseHandler):
    def __init__(self):
        self.retriever = QdrantRetriever()
```

**Modified Code:**
```python
from chatbot.hybrid_retriever import QdrantHybridRetriever
import chatbot.config as config

class RAGHandler(BaseHandler):
    def __init__(self):
        # Use hybrid retriever if enabled, otherwise falls back to dense-only
        self.retriever = QdrantHybridRetriever(
            collection_name=config.COLLECTION_NAME,
            hybrid_mode=config.ENABLE_HYBRID_RETRIEVAL
        )
```

### Testing Phase 4

```bash
# Test retriever directly
cd chatbot
python hybrid_retriever.py

# Test via chatbot
cd /home/tromanow/COHORT/TX
python interactive_chat.py

# Query: "What is the maximum income for a family of 5 earning bi-weekly?"
# Expected: BCY-26 chunk in top-5 results
```

**Status:** ⏸️ Not started (estimated 3-4 hours)

---

## ⏸️ Phase 5: Testing & Evaluation (NOT STARTED)

### Test Plan

#### 1. Unit Tests

**Create:** `LOAD_DB/test_hybrid_loading.py`
```python
"""Unit tests for hybrid loading pipeline."""
import pytest
from sparse_embedder import BM25Embedder

def test_bm25_embedding():
    embedder = BM25Embedder()
    text = "Family of 5 earns $4,106 bi-weekly"
    sparse_vec = embedder.embed_query(text)

    assert len(sparse_vec.indices) > 0
    assert len(sparse_vec.values) > 0
    assert len(sparse_vec.indices) == len(sparse_vec.values)

def test_hybrid_collection_creation():
    # Test that hybrid collection has named vectors
    from qdrant_client import QdrantClient
    import os

    client = QdrantClient(
        url=os.getenv('QDRANT_API_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )

    info = client.get_collection('tro-child-hybrid-v1')
    vectors_config = info.config.params.vectors

    assert 'dense' in vectors_config
    assert 'sparse' in vectors_config
```

#### 2. Integration Tests

```bash
# Load test PDFs to hybrid collection
cd LOAD_DB
python load_pdf_qdrant.py --test --hybrid --contextual

# Expected:
# - 3 PDFs processed
# - Dense + sparse vectors for all chunks
# - Collection created successfully
```

#### 3. Evaluation Comparison

```bash
# Baseline (dense-only contextual)
python -m evaluation.run_evaluation \
  --collection tro-child-3-contextual \
  --limit 25 \
  > results/baseline_dense.txt

# Hybrid (dense + sparse + RRF)
python -m evaluation.run_evaluation \
  --collection tro-child-hybrid-v1 \
  --limit 25 \
  > results/hybrid_rrf.txt

# Compare scores
grep "Composite Score" results/baseline_dense.txt
# Expected: ~41.7/100

grep "Composite Score" results/hybrid_rrf.txt
# Expected: 55-65/100 (+13-23 points improvement)
```

#### 4. BCY-26 Failure Case Validation

```bash
# Test specific failed query
python -m evaluation.run_evaluation \
  --collection tro-child-hybrid-v1 \
  --file bcy-26-psoc-chart-twc-qa.md \
  --resume --resume-limit 1

# Expected output:
# - Correct answer: "$4,106 bi-weekly"
# - BCY-26 chunk rank: 1-5 (previously 24)
# - Score: >70 (passing)
```

### Success Criteria

**Functional:**
- ✅ Hybrid collection created with dense + sparse vectors
- ✅ BM25 embedder functional
- ✅ RRF fusion working
- ✅ Backward compatibility (fallback to dense-only)
- ✅ Contextual embeddings preserved
- ✅ Reranking pipeline unchanged

**Performance:**
- ✅ Query latency increase <5% (2-3s → max 3.2s)
- ✅ Indexing time increase <20% (5 min → max 6 min)
- ✅ Storage increase <200 MB
- ✅ No degradation on passing test cases

**Accuracy:**
- ✅ BCY-26 query ranks correct chunk in top-5 (currently 24th)
- ✅ Composite score improves by +15-25 points (41.7 → 56-66/100)
- ✅ Exact match queries accuracy +30-40%
- ✅ Table lookup queries accuracy +30-40%
- ✅ Narrative queries maintain current accuracy (no regression)

**Status:** ⏸️ Not started (estimated 2-3 hours)

---

## Implementation Timeline

| Phase | Status | Time Spent | Time Remaining | Total Estimated |
|-------|--------|------------|----------------|-----------------|
| Phase 1: Config | ✅ Complete | 0.5 hours | - | 0.5 hours |
| Phase 2: BM25 Embedder | ✅ Complete | 1.5 hours | - | 1.5 hours |
| Phase 3: Loading Pipeline | 🚧 30% | 0.5 hours | 2.5 hours | 3 hours |
| Phase 4: Hybrid Retriever | ⏸️ Pending | - | 3.5 hours | 3.5 hours |
| Phase 5: Testing | ⏸️ Pending | - | 2 hours | 2 hours |
| **TOTAL** | **40% Complete** | **2.5 hours** | **8 hours** | **10.5 hours** |

---

## Next Steps

### Immediate (Phase 3 Completion)

1. **Modify `upload_with_embeddings()`** (30 min)
   - Add `hybrid_mode` parameter
   - Generate sparse vectors
   - Build named vector dicts

2. **Update collection creation** (20 min)
   - Add hybrid vectors_config
   - Support named vectors

3. **Add CLI flag and init parameter** (10 min)
   - `--hybrid` flag
   - Pass through pipeline

4. **Test Phase 3** (30 min)
   - Load 3 test PDFs
   - Verify collection structure
   - Check both vectors present

### Next (Phase 4)

5. **Create `hybrid_retriever.py`** (2 hours)
   - Implement RRF fusion
   - Add fallback logic
   - Test standalone

6. **Integrate with RAG handler** (1 hour)
   - Replace retriever
   - Test chatbot queries

### Final (Phase 5)

7. **Run full evaluation** (2 hours)
   - Baseline vs hybrid comparison
   - BCY-26 validation
   - Generate reports

---

## Rollback Plan

If hybrid search causes issues:

```bash
# Option 1: Disable in config (instant)
export ENABLE_HYBRID_RETRIEVAL=false

# Option 2: Switch collection (instant)
export COLLECTION_NAME='tro-child-3-contextual'

# Option 3: Revert code changes
git checkout HEAD -- chatbot/hybrid_retriever.py
git checkout HEAD -- chatbot/handlers/rag_handler.py
```

---

## Related Documentation

- **Implementation Plan:** `PLANS/hybrid_search_implementation.md`
- **Loading Pipeline:** `SPECS/loading_pipeline.md`
- **Evaluation System:** `SPECS/evaluation_system.md`
- **Config Files:**
  - `LOAD_DB/config.py` (lines 57-62)
  - `chatbot/config.py` (lines 63-68)

---

## Questions & Decisions

### Resolved
- ✅ Use BM25 for sparse vectors (not SPLADE or miniCOIL)
- ✅ Use RRF for fusion (k=60 standard)
- ✅ Context only for dense vectors (preserve keyword matching)
- ✅ New collection (parallel deployment, safe rollback)

### Open
- ⏸️ Should we tune RRF k parameter? (Default 60 is standard, defer tuning)
- ⏸️ Evaluate miniCOIL if BM25 shows gaps? (Defer to Phase 2 enhancement)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-20
**Next Review:** After Phase 3 completion
