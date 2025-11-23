# Hybrid Search Implementation Plan
## Texas Child Care RAG System Enhancement

**Date:** January 2025
**Status:** Design & Recommendation
**Current System:** Dense vector-only retrieval with 3-tier contextual embeddings
**Proposed Enhancement:** Hybrid search (Dense + Sparse vectors) with RRF fusion

---

## Executive Summary

**Problem:** Current dense-only vector search fails on exact keyword matching, resulting in documented failures like the BCY-26 query (correct chunk ranks 24th, outside retrieval window).

**Solution:** Implement hybrid search combining dense embeddings (semantic) with sparse vectors (keyword matching) using Reciprocal Rank Fusion (RRF).

**Impact:**
- Expected composite score improvement: 41.7 → 55-65 (+13-23 points)
- BCY-26 failure case: rank 24 → top-5 ✅
- Exact match queries: +40-50% accuracy
- Query latency: <1% increase (+20ms)
- Storage: +50-80 MB (negligible)

**Effort:** 10-15 hours (5 phases)

**Risk:** Low - new collection (no production impact), easy rollback, proven technology

---

## 1. CURRENT SYSTEM ANALYSIS

### Architecture
```
Query → Dense Retrieval (OpenAI, top-30)
     → LLM Reranking (GROQ, adaptive 5-12)
     → Generation
     → Answer
```

**Components:**
- **Vector DB:** Qdrant `tro-child-3-contextual`
- **Dense Embeddings:** OpenAI `text-embedding-3-small` (1536-dim)
- **Contextual Enhancement:** 3-tier hierarchy (Master + Document + Chunk contexts)
- **Retrieval:** Cosine similarity, threshold 0.3, top-30
- **Reranking:** GROQ `openai/gpt-oss-120b` (adaptive top-k)

**Statistics:**
- 37 PDFs, ~2,240 chunks
- Chunk size: 1000 chars, 200 overlap
- Collection size: ~19 MB

### Current Limitations

#### A. Exact Keyword Failures
**Problem:** Dense embeddings struggle with exact matches

**Examples:**
1. **Document IDs:** "BCY-26", "Form 2822", "PD-1034-A"
2. **Family Size Lookups:** "family size 12", "household of 8"
3. **Acronyms:** TANF, CCDF, PSOC, TWC, SMI (may retrieve wrong context)
4. **Program Names:** "Texas Rising Star", "CCMS"

**Documented Failure:**
- Query: "What is the maximum income for a family of 5 earning bi-weekly?"
- Correct answer: $4,106 (BCY 2026 table)
- Current rank: **24th** (outside top-20 retrieval window)
- Retrieved instead: $3,918 (from older 85% SMI table - wrong)

#### B. Table Lookup Failures
**Problem:** Table cells like "$4,106" lack narrative context for dense embeddings

**Root Cause:**
- Sparse data (numbers, dollar amounts) have low semantic richness
- Older verbose documents score higher semantically despite being wrong
- Exact value matching needed for table lookups

#### C. Numerical Threshold Queries
**Problem:** Dense search struggles with ranges and exact values

**Examples:**
- "families earning less than $50,000"
- "children aged 3-5"
- "ratios of 1:12"

---

## 2. HYBRID SEARCH SOLUTION

### Why Hybrid Works

**Complementary Strengths:**

| Method | Strengths | Weaknesses |
|--------|-----------|------------|
| **Dense** | Semantic understanding, context, synonyms, typo-resilient | Exact keywords, numerical precision, rare terms |
| **Sparse** | Exact keywords, acronyms, IDs, numerical matching | No semantic understanding, synonym blind, typo-sensitive |

**Fusion Benefits:**
- **Precision:** Exact matches for "BCY-26", "family size 12", "$4,106"
- **Recall:** Semantic matches for "explain eligibility", "income limits"
- **Robustness:** Handles both lookup and conceptual queries

### Sparse Vector Options

#### Recommended: BM25
**Pros:**
- Fast (~1ms per chunk, no GPU)
- Qdrant native IDF support
- Interpretable scoring
- Proven algorithm

**Cons:**
- No semantic expansion (exact tokens only)
- Typo-sensitive

**Best For:** Exact keyword matching (our primary need)

#### Alternative: miniCOIL
**Pros:**
- Fast (~50ms per chunk, CPU)
- Outperforms BM25 on BEIR
- Qdrant-native integration

**Cons:**
- Requires embedding computation
- Slower than BM25

**When to Consider:** If BM25 shows semantic expansion gaps after MVP

#### Skip: SPLADE
**Cons:**
- Too slow (500ms per chunk, requires GPU)
- Domain mismatch risk
- Overkill (LLM reranking already provides semantic scoring)

### Fusion Method: RRF

**Reciprocal Rank Fusion (RRF):**
```
RRF_score = Σ (1 / (k + rank_i))
where k = 60 (standard), rank_i = position in retrieval list i
```

**Why RRF:**
- Industry standard (Qdrant, OpenSearch, Elasticsearch)
- Rank-based (no score normalization issues)
- Robust, simple (one parameter: k=60)
- Qdrant Query API built-in

**Alternative:** Weighted fusion (only if RRF over-relies on sparse)

---

## 3. ARCHITECTURE DESIGN

### Collection Structure

**New Collection:** `tro-child-hybrid-v1` (parallel to existing)

```python
vectors_config = {
    "dense": VectorParams(
        size=1536,                    # OpenAI text-embedding-3-small
        distance=Distance.COSINE
    ),
    "sparse": VectorParams(
        size=30000,                   # BM25 vocabulary size
        distance=Distance.DOT,
        on_disk=True,                 # Memory optimization
        modifier=Modifier.IDF         # Enable BM25 IDF
    )
}
```

**Why New Collection:**
- No production impact
- Easy A/B testing (contextual vs hybrid)
- Safe rollback (switch collection names)

### Contextual Embeddings Integration

**Critical Decision:** Context only for dense vectors

```python
# Dense embedding (with 3-tier context for semantic richness)
dense_text = f"{master_context}\n{document_context}\n{chunk_context}\n{chunk_text}"
dense_vector = openai_embedder.embed(dense_text)

# Sparse embedding (no context, for exact keyword matching)
sparse_text = chunk_text  # Original chunk only
sparse_vector = bm25_embedder.embed(sparse_text)
```

**Rationale:**
- Dense: Context improves semantic matching
- Sparse: No context preserves exact keyword matching
- Fusion: Combines semantic richness with keyword precision

### Pipeline Flow

```
Query
  ↓
Dense Embedding (OpenAI) + Sparse Embedding (BM25)
  ↓
Qdrant Query API: Prefetch both → RRF Fusion
  ↓
Top-30 Candidates
  ↓
LLM Reranking (GROQ, unchanged)
  ↓
Adaptive Top-K Selection (5-12, unchanged)
  ↓
Generation (unchanged)
  ↓
Answer + Citations
```

**No Changes Needed:** Reranker, generator, adaptive selection all work unchanged!

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Setup & Configuration (1-2 hours)

**New Files:**
- `LOAD_DB/sparse_embedder.py` - BM25 embedder class
- `chatbot/hybrid_retriever.py` - Hybrid retrieval logic

**Modified Files:**
- `LOAD_DB/config.py` - Add hybrid settings
- `chatbot/config.py` - Add fusion settings

**Configuration:**
```python
# LOAD_DB/config.py
ENABLE_HYBRID_SEARCH = True
HYBRID_COLLECTION_NAME = 'tro-child-hybrid-v1'
SPARSE_EMBEDDER_TYPE = 'bm25'
BM25_VOCABULARY_SIZE = 30000
SPARSE_ON_DISK = True

# chatbot/config.py
ENABLE_HYBRID_RETRIEVAL = True
COLLECTION_NAME = 'tro-child-hybrid-v1'
FUSION_METHOD = 'rrf'
RRF_K = 60
HYBRID_PREFETCH_LIMIT = 100
RETRIEVAL_TOP_K = 30
```

### Phase 2: Sparse Embedder Implementation (2-3 hours)

**File:** `LOAD_DB/sparse_embedder.py`

**Key Components:**
```python
class BM25Embedder:
    def __init__(self):
        self.tokenizer = self._build_tokenizer()

    def embed(self, texts: List[str]) -> List[SparseVector]:
        """Convert texts to BM25 sparse vectors"""
        vectors = []
        for text in texts:
            # Tokenize
            tokens = self._tokenize(text)
            # Count term frequencies
            term_freqs = Counter(tokens)
            # Qdrant sparse format
            sparse_vec = SparseVector(
                indices=list(term_freqs.keys()),
                values=list(term_freqs.values())
            )
            vectors.append(sparse_vec)
        return vectors
```

**Deliverable:** Working BM25 embedder with unit tests

### Phase 3: Loading Pipeline Modifications (3-4 hours)

**Modified Files:**
- `LOAD_DB/load_pdf_qdrant.py` - Add `--hybrid` flag
- `LOAD_DB/shared/qdrant_uploader.py` - Add sparse vector upload

**Key Changes:**
```python
# Collection creation
def create_hybrid_collection(client, collection_name):
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(size=1536, distance=Distance.COSINE),
            "sparse": VectorParams(size=30000, distance=Distance.DOT,
                                   on_disk=True, modifier=Modifier.IDF)
        }
    )

# Upload modification
def upload_with_embeddings(..., hybrid_mode=False, sparse_embedder=None):
    dense_vectors = embeddings_model.embed_documents(texts)

    if hybrid_mode:
        sparse_vectors = sparse_embedder.embed(texts)

    points = [
        PointStruct(
            id=idx,
            vector={"dense": dense_vec, "sparse": sparse_vec},
            payload={...}
        )
        for idx, (dense_vec, sparse_vec) in enumerate(zip(dense_vectors, sparse_vectors))
    ]
```

**Command:**
```bash
python load_pdf_qdrant.py --hybrid --contextual
```

**Deliverable:** Load 3 test PDFs to hybrid collection

### Phase 4: Hybrid Retriever Implementation (3-4 hours)

**File:** `chatbot/hybrid_retriever.py`

**Key Components:**
```python
class QdrantHybridRetriever:
    def __init__(self, collection_name, hybrid_mode=True):
        self.client = QdrantClient(...)
        self.embeddings = OpenAIEmbeddings(...)
        self.sparse_embedder = BM25Embedder()
        self.hybrid_mode = hybrid_mode

    def search(self, query: str, top_k: int = 30):
        if not self.hybrid_mode:
            return self._dense_search(query, top_k)

        # Generate both query vectors
        dense_query = self.embeddings.embed_query(query)
        sparse_query = self.sparse_embedder.embed(query)

        # Qdrant Query API with RRF fusion
        results = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                {"query": dense_query, "using": "dense", "limit": 100},
                {"query": sparse_query, "using": "sparse", "limit": 100}
            ],
            query={"fusion": "rrf", "rrf": {"k": 60}},
            limit=top_k,
            score_threshold=config.MIN_SCORE_THRESHOLD
        )

        return self._format_results(results)
```

**Integration:**
- Modify `chatbot/handlers/rag_handler.py` to use `QdrantHybridRetriever`
- Keep fallback to dense-only on error

**Deliverable:** Working hybrid retrieval with backward compatibility

### Phase 5: Testing & Evaluation (2-3 hours)

**Unit Tests:**
```python
def test_bm25_embedding():
    embedder = BM25Embedder()
    text = "Family of 5 earns $4,106 bi-weekly"
    sparse_vec = embedder.embed(text)
    assert "family" in sparse_vec.indices
    assert "$4,106" in sparse_vec.indices

def test_hybrid_retrieval():
    retriever = QdrantHybridRetriever(collection='tro-child-hybrid-v1')
    results = retriever.search("What is BCY-26?", top_k=10)
    # Check BCY-26 document in top-5
    assert any("BCY-26" in r['filename'] for r in results[:5])
```

**Load Full Dataset:**
```bash
cd LOAD_DB
python load_pdf_qdrant.py --hybrid --contextual --clear
# Expected: ~5-7 minutes, 2,240 chunks
```

**Evaluation Comparison:**
```bash
# Baseline (dense-only)
python -m evaluation.run_evaluation --collection tro-child-3-contextual > baseline.txt

# Hybrid
python -m evaluation.run_evaluation --collection tro-child-hybrid-v1 > hybrid.txt

# Compare
grep "Composite Score" baseline.txt  # Expect: ~41.7/100
grep "Composite Score" hybrid.txt    # Expect: 55-65/100

# Test BCY-26 failure case
python -m evaluation.run_evaluation --resume --resume-limit 1 --collection tro-child-hybrid-v1
# Verify: Correct answer, chunk rank top-5
```

**Deliverable:** Passing test suite + evaluation report

---

## 5. EXPECTED IMPROVEMENTS

### Quantitative Metrics

| Metric | Dense-Only | Hybrid (Expected) | Improvement |
|--------|------------|-------------------|-------------|
| **Composite Score** | 41.7/100 | 55-65/100 | **+13-23 points** |
| **Exact Match Queries** | 30% | 70-80% | +40-50% |
| **Table Lookup Accuracy** | 45% | 75-85% | +30-40% |
| **Acronym Precision** | 60% | 85-90% | +25-30% |
| **BCY-26 Chunk Rank** | **24th** | **Top-5** | ✅ **Fixed** |
| **Query Latency** | 2-3s | 2-3s (+20ms) | <1% increase |
| **Storage** | 19 MB | 70-100 MB | Negligible |

### Qualitative Benefits

1. **Robustness to Query Types**
   - Lookup queries ("BCY-26 table") → sparse match
   - Conceptual queries ("explain eligibility") → dense match
   - Hybrid queries ("family of 5 income limits") → both contribute

2. **Reduced False Positives**
   - Sparse constraint ensures exact keywords present
   - Dense-only may retrieve semantically similar but factually wrong content

3. **Better Table Retrieval**
   - Table cells with sparse keywords ("$4,106", "family of 5") rank higher
   - Directly addresses BCY-26 failure case

4. **Acronym Disambiguation**
   - Sparse ensures exact acronym match ("PSOC")
   - Dense provides semantic context differentiation

---

## 6. PERFORMANCE & COST

### Indexing Cost

**Current (Dense-Only):**
- OpenAI embeddings: ~$0.22 (2.24M tokens)
- Time: ~5 minutes

**Hybrid (Dense + BM25):**
- Dense: $0.22 (same)
- BM25: Local computation, ~2 seconds
- **Total:** $0.22 (unchanged), ~5 minutes (BM25 adds <1%)

### Query Cost

**Current (Dense-Only):**
- Dense embedding: ~50ms
- Qdrant search: ~20ms
- LLM reranking: ~500ms
- Generation: ~1-2s
- **Total:** ~2-3s

**Hybrid (Dense + BM25 + RRF):**
- Dense embedding: ~50ms
- Sparse embedding: ~1ms (BM25 tokenization)
- Qdrant hybrid search: ~40ms (2 prefetches + RRF)
- LLM reranking: ~500ms
- Generation: ~1-2s
- **Total:** ~2-3s (+20ms, <1% increase)

### Storage Overhead

**Current:** 19 MB (dense vectors + metadata)

**Hybrid:** 70-100 MB (+50-80 MB for sparse vectors)
- With `on_disk=True` and Qdrant compression: 5-6x reduction
- Negligible for modern storage

---

## 7. RISKS & MITIGATION

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Sparse over-retrieval** | Keyword spam matches | RRF requires ranking in BOTH dense/sparse; LLM reranking filters |
| **Score normalization** | Fusion issues | RRF uses rank-based (no normalization needed) |
| **Qdrant API changes** | Breaking changes | Pin Qdrant version, monitor release notes |
| **Context confusion** | Dense/sparse mismatch | Context only for dense, clean text for sparse |

### Performance Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Query latency** | +20ms per query | BM25 overhead negligible (<1%), acceptable |
| **Indexing time** | +2 seconds (BM25) | Negligible for batch loading |
| **Memory consumption** | +50-80 MB | `on_disk=True` for sparse vectors |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Config complexity** | More tuning knobs | Use proven defaults (RRF k=60, prefetch=100) |
| **Baseline shift** | Hard to compare | Keep existing collection for A/B testing |
| **False improvement** | Hybrid may hurt narrative queries | Stratify evaluation by query type |

**Overall Risk Assessment:** **Low Risk, High Reward**
- Minimal performance impact
- Major accuracy gains on documented failures
- Easy rollback (collection switching)
- Proven technology (RRF industry standard)

---

## 8. CONFIGURATION OPTIONS

### Command-Line Flags

**Loading:**
```bash
# Hybrid with contextual
python load_pdf_qdrant.py --hybrid --contextual

# Test mode (3 PDFs)
python load_pdf_qdrant.py --test --hybrid --contextual

# Specify sparse type
python load_pdf_qdrant.py --hybrid --sparse-type minicoil
```

**Chatbot:**
```bash
# Use hybrid collection
python interactive_chat.py --collection tro-child-hybrid-v1

# Fallback to dense-only
python interactive_chat.py --collection tro-child-3-contextual
```

**Evaluation:**
```bash
# Evaluate hybrid
python -m evaluation.run_evaluation --collection tro-child-hybrid-v1

# Compare collections
python -m evaluation.run_evaluation --collection tro-child-3-contextual > dense.txt
python -m evaluation.run_evaluation --collection tro-child-hybrid-v1 > hybrid.txt
diff dense.txt hybrid.txt
```

### Environment Variables

```bash
# Override collection
export COLLECTION_NAME='tro-child-hybrid-v1'

# Disable hybrid (fallback to dense)
export ENABLE_HYBRID_RETRIEVAL=false

# Adjust fusion method
export FUSION_METHOD='weighted'  # Default: 'rrf'
export RRF_K=60                  # Default: 60
```

### Tuning Parameters (Advanced)

**Minimal Tuning Required:**
- RRF k=60 (standard, no tuning needed)
- Prefetch limit=100 (standard, only tune if performance issues)
- Top-k=30 (already tuned for reranker)

**Only If Issues:**
- Weighted RRF (if sparse over-retrieves)
- Prefetch limits (if latency becomes issue)
- Score thresholds (if RRF score distribution differs)

---

## 9. ROLLOUT STRATEGY

### Parallel Deployment

**Phase 1: Load Hybrid Collection**
```bash
python load_pdf_qdrant.py --hybrid --contextual
# Creates: tro-child-hybrid-v1
# Keeps: tro-child-3-contextual (unchanged)
```

**Phase 2: A/B Testing**
```bash
# Test both collections
python -m evaluation.run_evaluation --collection tro-child-3-contextual > dense_scores.txt
python -m evaluation.run_evaluation --collection tro-child-hybrid-v1 > hybrid_scores.txt

# Compare scores
diff dense_scores.txt hybrid_scores.txt
```

**Phase 3: Switch Production Config**
```bash
# Update config
export COLLECTION_NAME='tro-child-hybrid-v1'

# Test production chatbot
python interactive_chat.py
# Query: "What is the maximum income for a family of 5 earning bi-weekly?"
# Expected: "$4,106" from BCY-26 table (rank top-5)
```

**Phase 4: Monitor & Rollback if Needed**
```bash
# If issues, instant rollback
export COLLECTION_NAME='tro-child-3-contextual'

# Or disable hybrid mode
export ENABLE_HYBRID_RETRIEVAL=false
```

### Success Criteria

✅ **Functional Requirements:**
- Hybrid collection created with dense + sparse vectors
- BM25 embedder functional
- RRF fusion working
- Backward compatibility (fallback to dense-only)
- Contextual embeddings preserved
- Reranking pipeline unchanged

✅ **Performance Requirements:**
- Query latency increase <5% (2-3s → max 3.2s)
- Indexing time increase <20% (5 min → max 6 min)
- Storage increase <200 MB
- No degradation on passing test cases

✅ **Accuracy Requirements:**
- BCY-26 query ranks correct chunk in top-5 (currently 24th)
- Composite score improves by +15-25 points (41.7 → 56-66/100)
- Exact match queries accuracy +30-40%
- Table lookup queries accuracy +30-40%
- Narrative queries maintain current accuracy (no regression)

---

## 10. FUTURE OPTIMIZATIONS (Post-MVP)

### Phase 2 Enhancements

**A. Evaluate miniCOIL**
- If BM25 insufficient for semantic expansion
- Benchmark speed impact (~50ms overhead)
- Compare accuracy improvements

**B. Weighted Fusion**
- If RRF over-relies on sparse (keyword spam)
- Assign weights: dense (0.6) vs sparse (0.4)
- Grid search on eval set

**C. Cross-Encoder Reranking**
- If LLM reranking latency becomes issue (>5s)
- Pipeline: RRF (top-100) → Cross-Encoder (top-20) → LLM (adaptive 5-12)
- Model: `ms-marco-MiniLM-L-6-v2` (fast, CPU)

**D. Query-Type Routing**
- Different fusion strategies per query type
- Lookup queries → sparse-heavy (α=0.3 dense, 0.7 sparse)
- Narrative queries → dense-heavy (α=0.8 dense, 0.2 sparse)
- Requires intent classifier modification

### Phase 3 Enhancements

**A. Dynamic Fusion Tuning**
- LLM predicts optimal fusion weights per query
- Adaptive α based on query complexity

**B. Multi-Retriever Ensemble**
- Add third retriever (TF-IDF for legacy)
- Three-way RRF fusion

**C. Domain-Specific Sparse Model**
- Fine-tune SPLADE/miniCOIL on Texas childcare domain
- Train on 2,387-question evaluation dataset

---

## 11. APPENDIX

### A. Qdrant Query API Example

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Query

results = client.query_points(
    collection_name="tro-child-hybrid-v1",
    prefetch=[
        Prefetch(query=dense_vector, using="dense", limit=100),
        Prefetch(query=sparse_vector, using="sparse", limit=100)
    ],
    query=Query(fusion="rrf", rrf={"k": 60}),
    limit=30,
    score_threshold=0.3
)
```

### B. BM25 Algorithm

```
score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

where:
  IDF(qi) = log((N - df(qi) + 0.5) / (df(qi) + 0.5))
  k1 = 1.2 (term frequency saturation)
  b = 0.75 (length normalization)
```

### C. RRF Algorithm

```python
def rrf_fusion(results_lists, k=60):
    scores = defaultdict(float)
    for results in results_lists:
        for rank, doc_id in enumerate(results, start=1):
            scores[doc_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### D. Related Documentation

- `SPECS/contextual_retrieval_implementation.md` - 3-tier context design
- `SPECS/evaluation_system_implementation.md` - LLM-as-a-judge system
- `SPECS/item_level_chunking_implementation.md` - Docling table extraction
- `LOAD_DB/config.py` - Vector DB settings
- `chatbot/config.py` - Retrieval settings

---

## 12. DECISION SUMMARY

### ✅ Recommended Decisions

1. **Sparse Embedder:** BM25 (simple, fast, proven)
2. **Fusion Method:** RRF (standard, robust, Qdrant native)
3. **Reranking:** Keep LLM reranking (already working well)
4. **Rollout:** New collection (parallel to existing, safe rollback)
5. **Context Strategy:** Dense only (preserves keyword matching for sparse)

### ⏸️ Defer to Phase 2

- miniCOIL evaluation (only if BM25 shows gaps)
- Weighted fusion (only if RRF issues)
- Cross-encoder reranking (only if latency issue)
- Query-type routing (defer until MVP validated)

### ❌ Not Recommended

- SPLADE (too slow, domain mismatch)
- Migrate existing collection (risky, no rollback)
- Complex tuning (use proven defaults first)

---

## FINAL RECOMMENDATION

**Proceed with Hybrid Search MVP:**
- BM25 sparse vectors
- RRF fusion
- New collection (`tro-child-hybrid-v1`)
- 10-15 hours implementation
- Expected +15-25 point improvement
- Low risk, high reward

**Next Steps:**
1. Review and approve this plan
2. Spike BM25 implementation (2 days)
3. Validate BCY-26 fix
4. Run full evaluation comparison
5. Deploy to production if successful

---

**END OF PLAN**
