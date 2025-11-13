# Real-Time Web Browsing Chatbot Prototype - Design Summary

**Date:** 2025-11-12
**Status:** Planning Phase
**Goal:** Add live web search capability to complement existing vector DB RAG system

---

## Problem Statement

Current system uses **batch scrape → index → retrieve** pattern with Qdrant vector DB. This works well for static content but has limitations:
- Content can become stale
- Limited to pre-scraped documents
- Cannot answer queries about current/live information
- No access to external websites

**Proposed solution:** Add real-time web browsing capability using Tavily API.

---

## Architecture Evolution

### Current System
```
User Query → IntentRouter → RAGHandler (Qdrant vector DB)
                         → LocationSearchHandler (template response)
```

### Option A: Strict Routing (Initial Design)
```
User Query → IntentRouter → RAGHandler (vector DB)
                         → LocationSearchHandler (template)
                         → TavilyHandler (live web) ← NEW
```
**Problem:** Naive - fails when query seems like RAG but content isn't in DB

### Option B: Hybrid Handler (Refined Design) ⭐ RECOMMENDED
```
User Query → IntentRouter → HybridHandler (RAG + Tavily fallback)
                         → LocationSearchHandler (template)
```

**HybridHandler logic:**
1. Query vector DB first (fast, cheap)
2. Evaluate result quality (scores, count)
3. If insufficient → supplement with Tavily search
4. Generate answer from best available sources
5. Cite sources appropriately (PDF vs Web)

---

## Tool Comparison Analysis

### Custom Browsing (Playwright + BeautifulSoup)
- **Pros:** Full control, no external dependencies, no API costs
- **Cons:** High complexity, slower, maintenance burden
- **Effort:** 2-3 days implementation

### LangChain WebAgent
- **Pros:** Framework with tool orchestration
- **Cons:** Multiple LLM calls (3-7x), expensive, unpredictable, slow
- **Issue:** Adds orchestration overhead without adding capability
- **Key insight:** It's a framework that still needs search/browser tools - doesn't provide the actual browsing functionality

### Tavily API ⭐ SELECTED
- **Pros:** Purpose-built for AI/RAG, fast (2-3 sec), LLM-ready output, affordable
- **Cost:** ~$1 per 1K searches
- **Control:** Medium - you control generation, they handle search/extraction
- **Effort:** 2-3 hours implementation
- **Why it wins:** Direct search functionality without agent overhead

### Perplexity API
- **Pros:** Simplest (all-in-one), production-grade
- **Cons:** Black box, less control, higher cost (~$5/1K)
- **Use case:** Quick MVP testing

**Decision:** Tavily offers best balance of simplicity, control, and cost.

**Analogy:**
- LangChain WebAgent = Building a robot to drive a car
- Tavily = Uber (you pick destination, they drive)
- Perplexity = Taxi (tell them where, they figure it out)

---

## Hybrid Handler Implementation Design

### Quality Assessment Logic
```python
def _is_sufficient(self, rag_results):
    """Determine if RAG results are good enough"""
    return (
        len(rag_results) >= 3 and           # Minimum result count
        max(r['score'] for r in rag_results) > 0.7  # Confidence threshold
    )
```

### Fallback Flow
```python
def handle(self, query: str):
    # Try RAG first
    rag_results = self.retriever.search(query)

    # Evaluate quality
    if self._is_sufficient(rag_results):
        return self.generate(rag_results, source_type='vector_db')

    # Supplement with Tavily
    web_results = self.tavily.search(query)
    combined = self._merge_sources(rag_results, web_results)

    return self.generate(
        combined,
        source_type='hybrid',
        note='Supplemented with live web search'
    )
```

### Source Attribution
- Vector DB sources: `[PDF: document.pdf, page X]`
- Web sources: `[Web: title, URL, accessed: timestamp]`
- Mixed responses indicate source type per citation

---

## Why Hybrid Handler Over Strict Routing

**Problem with strict routing:**
- "What are the new 2025 childcare rules?" → Looks like RAG query
- But content might not be indexed yet
- User gets "no results" when web has the answer

**Hybrid solution:**
- System tries RAG first
- Detects insufficient results automatically
- Supplements with Tavily seamlessly
- User doesn't need to know about routing

**Real-world scenarios:**
1. **Query looks like RAG but isn't in DB** - "What are the new 2025 childcare rules?"
2. **Partial info in both** - "How do I apply?" (process in DB, current form link on web)
3. **Ambiguous queries** - "Tell me about childcare assistance" (could need both)

---

## Implementation Plan Summary

### Files to Create
1. `chatbot/handlers/hybrid_handler.py` - Main implementation (~120 lines)
2. `test_hybrid_handler.py` - Test suite (~80 lines)

### Files to Modify
1. `requirements.txt` - Add `tavily-python`
2. `chatbot/config.py` - Add Tavily settings
3. `chatbot/intent_router.py` - Route to HybridHandler instead of RAGHandler
4. `chatbot/chatbot.py` - Initialize HybridHandler
5. `chatbot/handlers/__init__.py` - Export HybridHandler
6. `CLAUDE.md` - Document new capability
7. `.env` - Add `TAVILY_API_KEY`

### Configuration Additions
```python
# chatbot/config.py
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
TAVILY_SEARCH_DEPTH = 'advanced'  # or 'basic'
TAVILY_MAX_RESULTS = 5
TAVILY_TIMEOUT = 10

# Hybrid handler thresholds
RAG_MIN_RESULTS = 3
RAG_MIN_CONFIDENCE = 0.7
HYBRID_MODE_ENABLED = True
```

### Effort Estimate
- Core implementation: 2-3 hours
- Testing: 30 minutes
- Documentation: 30 minutes
- **Total: ~3-4 hours**

---

## Key Design Decisions

### 1. Hybrid over Strict Routing
**Rationale:** System should automatically supplement RAG with web when needed, not force user to understand routing

### 2. RAG-First Strategy
**Rationale:** Vector DB is faster and cheaper - use Tavily only when necessary

### 3. Confidence-Based Fallback
**Rationale:** Let reranker scores guide whether results are sufficient

### 4. Transparent Source Attribution
**Rationale:** User should know if answer came from indexed docs vs live web

### 5. Location Handler Stays Separate
**Rationale:** Template responses for facility search don't need RAG or web search

### 6. No Functional Changes to Existing Chatbot
**Rationale:** RAG pipeline remains untouched - this is an extension, not a modification
- Existing RAGHandler code can be reused inside HybridHandler
- Same retriever, reranker, generator instances
- Same response format

---

## Comparison: Vector DB vs. Real-Time Browsing

| Aspect | Vector DB (Current) | Real-Time Browsing (New) | Hybrid (Proposed) |
|--------|---------------------|--------------------------|-------------------|
| **Latency** | ~2 sec | ~5-10 sec | 2-5 sec (adaptive) |
| **Content freshness** | Static (last scrape) | Always current | Best of both |
| **Coverage** | Pre-scraped only | Any URL | Comprehensive |
| **Accuracy** | High (indexed) | Variable | High |
| **Cost** | Low (embeddings once) | Higher (per query) | Optimized |
| **Best for** | Known domain content | Live updates | All scenarios |

---

## Success Criteria

✅ Hybrid handler responds to queries not in vector DB
✅ RAG results used when available (minimize Tavily costs)
✅ Automatic fallback to Tavily when RAG insufficient
✅ Clear source attribution (PDF vs Web)
✅ Response format consistent with existing handlers
✅ Graceful error handling (API failures, timeouts)
✅ No breaking changes to existing functionality

---

## Implementation Phases

### Phase 1: Documentation & Setup
- Create this design document
- Add Tavily dependency
- Get API key, configure environment

### Phase 2: Core Implementation
- Add Tavily configuration to config.py
- Create HybridHandler class
- Implement RAG-first + fallback logic
- Add quality assessment
- Handle source merging

### Phase 3: Integration
- Update IntentRouter to use HybridHandler
- Update chatbot.py initialization
- Update handler exports

### Phase 4: Testing
- Create test suite
- Test RAG-only scenarios
- Test fallback scenarios
- Test error handling
- Manual testing with real queries

### Phase 5: Documentation
- Update CLAUDE.md
- Document behavior and configuration
- Add usage examples

---

## Future Enhancements (Out of Scope)

- Parallel querying (RAG + Tavily simultaneously for speed)
- Result caching (avoid re-querying same content)
- Multi-source reranking (score RAG + web results together)
- Agentic browsing (follow links, multi-hop reasoning)
- Custom web scraping for specific domains
- A/B testing framework for RAG vs Hybrid performance

---

## Open Questions

1. ✅ Should we use strict routing or hybrid? → **Hybrid (decided)**
2. What confidence threshold triggers Tavily fallback? → **Proposal: 0.7**
3. Minimum result count before fallback? → **Proposal: 3**
4. Should we always show source type, or only on hybrid? → **TBD**
5. Do location queries need web fallback? → **Likely no**

---

## Cost Analysis

**Assumptions:**
- 1000 queries/month
- 30% require Tavily fallback (RAG insufficient)
- Tavily: $1 per 1K searches

**Monthly cost:**
- RAG-only queries (700): $0
- Tavily fallback (300): $0.30
- **Total: ~$0.30/month**

**Comparison:**
- Always using Tavily: $1/month
- Always using Perplexity: $5/month
- Hybrid approach: **$0.30/month** (70% savings vs pure Tavily)

---

## Next Steps

1. ✅ Create this design document
2. Get Tavily API key (tavily.com)
3. Implement HybridHandler
4. Update IntentRouter
5. Test with edge cases (content not in DB)
6. Monitor Tavily usage/costs
7. Document user-facing behavior
8. Deploy and observe real-world performance

---

## References

- Current RAG implementation: `SPECS/chatbot_implementation.md`
- Scraper architecture: `SCRAPER/scraper.py`
- Tavily API: https://tavily.com
- Project documentation: `CLAUDE.md`

---

**This document captures the planning conversation and will be updated as implementation progresses.**
