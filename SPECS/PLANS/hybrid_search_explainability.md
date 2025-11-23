# Hybrid Search Explainability Enhancement

**Date:** 2025-11-21
**Status:** PROPOSAL
**Priority:** Medium (Optional enhancement)

---

## Problem Statement

Current hybrid search implementation uses Qdrant's server-side RRF fusion, which provides **zero transparency** into how results are ranked:

**What we get:**
```python
{
    'text': '...',
    'score': 0.5000,  # Final RRF score only
    'filename': '...'
}
```

**What we DON'T know:**
- ❌ Individual dense vector score
- ❌ Individual sparse vector score
- ❌ Which vector type contributed more to ranking
- ❌ Dense rank vs sparse rank in prefetch
- ❌ RRF calculation breakdown
- ❌ Whether result came from dense-only, sparse-only, or both

## Impact

### Debugging Challenges:
- Can't validate if sparse vectors are improving results
- Can't diagnose unexpected rankings
- Can't determine if keywords or semantics drove a result
- Can't tune vector contribution weights

### Research Limitations:
- No ablation studies (dense-only vs sparse-only vs hybrid)
- Can't measure relative contribution of each vector type
- Can't compare RRF effectiveness vs other fusion methods
- Can't identify when one vector type dominates

### Production Opacity:
- Users can't understand why results ranked in a certain order
- Difficult to explain system behavior to stakeholders
- Hard to identify when to use hybrid vs dense-only

---

## Proposed Solution: Optional Debug Mode

Add **optional parallel searches** with full score breakdown when `debug=True`.

### Architecture

```python
class QdrantHybridRetriever:
    def search(self, query: str, top_k: int = 20, debug: bool = False) -> List[Dict]:
        """
        Args:
            debug: If True, run parallel dense/sparse searches for comparison

        Returns:
            Standard results with optional 'debug_scores' key containing breakdown
        """
        if debug:
            return self._search_with_debug(query, top_k)
        else:
            return self._search_standard(query, top_k)

    def _search_standard(self, query: str, top_k: int) -> List[Dict]:
        """Current implementation - fast server-side RRF"""
        # Existing code unchanged
        pass

    def _search_with_debug(self, query: str, top_k: int) -> List[Dict]:
        """Debug mode - parallel searches with full breakdown"""

        # 1. Run dense-only search
        dense_results = self.client.search(
            collection_name=self.collection,
            query_vector=("dense", dense_query),
            limit=config.HYBRID_PREFETCH_LIMIT
        )

        # 2. Run sparse-only search
        sparse_results = self.client.search(
            collection_name=self.collection,
            query_vector=("sparse", sparse_query),
            limit=config.HYBRID_PREFETCH_LIMIT
        )

        # 3. Run hybrid search for actual results
        hybrid_results = self.client.query_points(
            # ... existing hybrid search code
        )

        # 4. Augment results with score breakdown
        return self._add_debug_scores(
            hybrid_results,
            dense_results,
            sparse_results
        )

    def _add_debug_scores(self, hybrid, dense, sparse) -> List[Dict]:
        """Add per-result score breakdown"""

        # Create lookup maps
        dense_map = {r.id: (i, r.score) for i, r in enumerate(dense)}
        sparse_map = {r.id: (i, r.score) for i, r in enumerate(sparse)}

        # Augment hybrid results
        for chunk in hybrid:
            chunk_id = chunk.get('id')  # Need to expose point IDs

            chunk['debug_scores'] = {
                'hybrid_score': chunk['score'],
                'dense_rank': dense_map.get(chunk_id, (None, None))[0],
                'dense_score': dense_map.get(chunk_id, (None, None))[1],
                'sparse_rank': sparse_map.get(chunk_id, (None, None))[0],
                'sparse_score': sparse_map.get(chunk_id, (None, None))[1],
                'in_dense': chunk_id in dense_map,
                'in_sparse': chunk_id in sparse_map,
                'source': self._determine_source(chunk_id, dense_map, sparse_map)
            }

        return hybrid

    def _determine_source(self, chunk_id, dense_map, sparse_map) -> str:
        """Determine which vector type(s) contributed"""
        in_dense = chunk_id in dense_map
        in_sparse = chunk_id in sparse_map

        if in_dense and in_sparse:
            return 'both'
        elif in_dense:
            return 'dense_only'
        elif in_sparse:
            return 'sparse_only'
        else:
            return 'unknown'
```

### Example Debug Output

```python
{
    'text': 'BCY-26 income eligibility table...',
    'score': 0.5000,
    'filename': 'bcy-26-income-eligibility.pdf',
    'debug_scores': {
        'hybrid_score': 0.5000,
        'dense_rank': 45,      # Ranked low in dense search
        'dense_score': 0.72,
        'sparse_rank': 2,       # Ranked high in sparse search!
        'sparse_score': 0.89,
        'in_dense': True,
        'in_sparse': True,
        'source': 'both'        # Sparse boosted this result
    }
}
```

---

## Implementation Changes

### Files Modified:

**1. `chatbot/hybrid_retriever.py`**
- Add `debug` parameter to `search()` method
- Split into `_search_standard()` and `_search_with_debug()`
- Add `_add_debug_scores()` helper
- Add `_determine_source()` helper
- **Lines added:** ~80-100

**2. `chatbot/handlers/rag_handler.py`**
- Pass `debug` flag through to retriever
- Include debug scores in debug_info output
- **Lines modified:** ~3-5

**3. `test_hybrid_retriever.py`**
- Add test cases for debug mode
- Validate score breakdown
- **Lines added:** ~30

### Technical Requirements:

1. **Expose Qdrant Point IDs**: Need to include point IDs in results for matching across searches
2. **Three API calls**: Dense, sparse, hybrid (vs current single call)
3. **Latency increase**: ~2-3x slower due to parallel searches
4. **Memory overhead**: Store 3 result sets temporarily

---

## Tradeoffs

| Aspect | Standard Mode | Debug Mode |
|--------|--------------|------------|
| **Latency** | ~500-700ms | ~1500-2000ms (+200%) |
| **Network calls** | 1 query_points | 3 searches (2 + 1) |
| **Transparency** | None | Full breakdown |
| **Use case** | Production | Research/debugging |
| **Code complexity** | Simple | Moderate |

---

## Use Cases

### Use Case 1: Validate Sparse Vector Contribution
**Scenario:** After deploying hybrid search, verify that sparse vectors are actually improving keyword matching.

**Debug output shows:**
```
Query: "What is BCY-26?"
Result #3: bcy-26-income-eligibility.pdf
  - Dense rank: 45 (weak semantic match)
  - Sparse rank: 2 (strong keyword match)
  - Source: both (sparse boosted it)

✅ Confirmed: Sparse vectors successfully boosted BCY-26 document
```

### Use Case 2: Diagnose Poor Rankings
**Scenario:** User complains that a relevant document isn't appearing.

**Debug output reveals:**
```
Query: "childcare subsidies"
Missing doc: texas-childcare-subsidy-guide.pdf
  - Dense rank: 89 (NOT in top 100 prefetch)
  - Sparse rank: 3 (in top 100)
  - Source: sparse_only
  - Hybrid score: Low (only one vector contributed)

🔍 Diagnosis: Document missing from dense prefetch, relying only on sparse
💡 Action: Increase HYBRID_PREFETCH_LIMIT or improve embeddings
```

### Use Case 3: Compare Fusion Methods
**Scenario:** Evaluate if RRF is optimal or if weighted fusion would be better.

**Debug data enables:**
- Export dense/sparse scores for 100 queries
- Calculate alternative fusion scores (weighted average, etc.)
- Compare ranking quality
- Data-driven decision on fusion method

### Use Case 4: A/B Testing Dense vs Hybrid
**Scenario:** Measure improvement from hybrid search vs dense-only.

**With debug mode:**
```python
# Compare dense_score vs hybrid_score across evaluation set
for query, expected_doc in eval_set:
    results = retriever.search(query, debug=True)

    # Find expected doc in results
    for r in results:
        if r['filename'] == expected_doc:
            print(f"Dense rank: {r['debug_scores']['dense_rank']}")
            print(f"Hybrid rank: {results.index(r)}")

# Quantify improvement: "Hybrid improves ranking by average 12 positions"
```

---

## Implementation Priority

**Recommendation: DEFER** until one of these occurs:

1. **Production issue**: Unexplained ranking behavior requiring diagnosis
2. **Research need**: Evaluation comparing dense vs hybrid effectiveness
3. **Optimization**: Need to tune prefetch limits or fusion parameters
4. **User demand**: Stakeholders request explainability features

**Rationale:**
- Current implementation works correctly
- Debug mode adds complexity without immediate benefit
- Can be added incrementally when needed
- Standard mode remains unchanged (no risk)

---

## Alternative Approaches

### Option 1: Custom RRF Implementation (Not Recommended)
Replace Qdrant's fusion with manual RRF in Python:

**Pros:**
- Full control and transparency by default
- Can customize fusion algorithm
- Can add weighted fusion easily

**Cons:**
- ❌ Much slower (client-side computation)
- ❌ More network traffic (fetch 200 candidates)
- ❌ Complex code to maintain
- ❌ Lose Qdrant's optimized implementation

### Option 2: Logging to File (Simpler Alternative)
Log individual searches when debug flag is set, analyze offline:

```python
if debug:
    # Log searches to file
    with open('debug_searches.jsonl', 'a') as f:
        f.write(json.dumps({
            'query': query,
            'dense_results': dense_results,
            'sparse_results': sparse_results,
            'hybrid_results': hybrid_results
        }))
```

**Pros:**
- Simpler implementation
- Can analyze patterns across queries
- No changes to return format

**Cons:**
- Not available in real-time
- Requires separate analysis step

---

## Success Metrics

If implemented, measure success by:

1. **Debug adoption rate**: How often `debug=True` is used
2. **Issue resolution**: Whether debug mode helps diagnose ranking issues
3. **Research insights**: Papers/reports using debug data
4. **Performance validation**: Confirm sparse vectors improve retrieval

---

## References

**Related Documents:**
- `SPECS/DOC/hybrid_search_phase4_complete.md` - Current implementation
- `SPECS/PLANS/hybrid_search_implementation.md` - Original plan

**Qdrant Documentation:**
- Hybrid Search: https://qdrant.tech/documentation/beginner-tutorials/hybrid-search-fastembed/
- Query API: https://qdrant.tech/documentation/concepts/hybrid-queries/

---

## Summary

**Problem:** Qdrant RRF fusion is a black box
**Solution:** Optional debug mode with parallel searches
**Tradeoff:** 3x latency increase when debug=True
**Recommendation:** Defer until specific need arises

This proposal adds **optional** explainability without affecting production performance.

---

**Document Version:** 1.0
**Author:** Claude (Sonnet 4.5)
**Date:** 2025-11-21
**Status:** Awaiting approval
