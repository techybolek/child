# LangGraph Phase 0: Migration Plan

**Date:** 2025-11-26
**Status:** Planning
**Goal:** Migrate current RAG pipeline to LangGraph with zero behavioral change
**Risk Level:** Low (same behavior, new framework)

## Success Criteria

1. **Evaluation parity:** All existing evaluation scores remain identical (±2%)
2. **API parity:** `TexasChildcareChatbot.ask()` returns identical response structure
3. **No new dependencies** beyond LangGraph core
4. **Feature flag ready:** `CONVERSATIONAL_MODE=false` yields stateless behavior

---

## Current Architecture Analysis

### Component Inventory

| Component | File | Purpose | LangGraph Mapping |
|-----------|------|---------|-------------------|
| `TexasChildcareChatbot` | `chatbot/chatbot.py` | Entry point, timing | Graph entry point |
| `IntentRouter` | `chatbot/intent_router.py` | Classify → route | Router node + conditional edge |
| `RAGHandler` | `chatbot/handlers/rag_handler.py` | Retrieve → Rerank → Generate | 3 nodes in sequence |
| `LocationSearchHandler` | `chatbot/handlers/location_handler.py` | Template response | Single node |
| `QdrantRetriever` | `chatbot/retriever.py` | Dense vector search | Wrapped in retrieve node |
| `QdrantHybridRetriever` | `chatbot/hybrid_retriever.py` | Dense + sparse RRF | Wrapped in retrieve node |
| `LLMJudgeReranker` | `chatbot/reranker.py` | LLM relevance scoring | Rerank node |
| `ResponseGenerator` | `chatbot/generator.py` | Answer generation | Generate node |

### Current Flow (Information Query)

```
ask(question)
    ↓
IntentRouter.route(question)
    ↓
IntentRouter.classify_intent(question)  → "information" or "location_search"
    ↓
handlers["information"].handle(question)  [RAGHandler]
    ↓
    ├── retriever.search(query, top_k=20)
    ├── reranker.rerank(query, chunks, top_k=7)
    └── generator.generate(query, chunks)
    ↓
return {answer, sources, response_type, action_items, processing_time}
```

### Current Flow (Location Query)

```
ask(question)
    ↓
IntentRouter.route(question)
    ↓
IntentRouter.classify_intent(question)  → "location_search"
    ↓
handlers["location_search"].handle(question)  [LocationSearchHandler]
    ↓
return {answer="template", sources=[], response_type="location_search", action_items=[link]}
```

---

## Target Architecture

### LangGraph State Definition

```python
# chatbot/graph/state.py

from typing import TypedDict, Literal

class RAGState(TypedDict):
    """Minimal state for stateless RAG pipeline"""

    # Input
    query: str                              # User's question

    # Routing
    intent: Literal["information", "location_search"] | None

    # Retrieval
    retrieved_chunks: list[dict]            # From Qdrant

    # Reranking
    reranked_chunks: list[dict]             # After LLM scoring

    # Generation
    answer: str | None
    sources: list[dict]

    # Response metadata
    response_type: str
    action_items: list[dict]

    # Debug (optional)
    debug_info: dict | None
```

### Graph Structure (Stateless Mode)

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         ↓
                    ┌─────────┐
                    │ CLASSIFY│  (intent classification)
                    └────┬────┘
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
        ┌──────────┐          ┌──────────┐
        │RETRIEVE  │          │ LOCATION │
        └────┬─────┘          └────┬─────┘
             ↓                     │
        ┌──────────┐               │
        │ RERANK   │               │
        └────┬─────┘               │
             ↓                     │
        ┌──────────┐               │
        │ GENERATE │               │
        └────┬─────┘               │
             ↓                     │
             └─────────┬───────────┘
                       ↓
                  ┌─────────┐
                  │   END   │
                  └─────────┘
```

---

## Implementation Plan

### File Structure

```
chatbot/
├── graph/                          # NEW: LangGraph implementation
│   ├── __init__.py
│   ├── state.py                    # RAGState TypedDict
│   ├── nodes/                      # Node implementations
│   │   ├── __init__.py
│   │   ├── classify.py             # Intent classification node
│   │   ├── retrieve.py             # Retrieval node
│   │   ├── rerank.py               # Reranking node
│   │   ├── generate.py             # Generation node
│   │   └── location.py             # Location template node
│   ├── edges.py                    # Conditional routing logic
│   └── builder.py                  # Graph construction
├── chatbot.py                      # MODIFY: Use graph instead of router
├── config.py                       # MODIFY: Add CONVERSATIONAL_MODE flag
└── ... (existing files unchanged)
```

### Step-by-Step Implementation

#### Step 1: Add LangGraph Dependency

**File:** `requirements.txt`

```
langgraph>=0.2.0
```

**Verification:** `pip install langgraph && python -c "from langgraph.graph import StateGraph; print('OK')"`

---

#### Step 2: Create State Definition

**File:** `chatbot/graph/state.py`

```python
from typing import TypedDict, Literal

class RAGState(TypedDict):
    """State for RAG pipeline graph"""

    # Input
    query: str
    debug: bool

    # Routing
    intent: Literal["information", "location_search"] | None

    # Retrieval (information path)
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]

    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]
    debug_info: dict | None
```

**Rationale:**
- Mirrors current response structure exactly
- No conversation history (stateless mode)
- Debug flag for evaluation compatibility

---

#### Step 3: Create Node Implementations

Each node wraps existing component logic with minimal changes.

**File:** `chatbot/graph/nodes/classify.py`

```python
def classify_node(state: RAGState) -> dict:
    """Classify intent using existing IntentRouter logic"""

    # Reuse existing classification logic
    from ...intent_router import IntentRouter

    # Create temporary router just for classification
    # (In production, this would be injected)
    router = IntentRouter()
    intent = router.classify_intent(state["query"])

    return {"intent": intent}
```

**File:** `chatbot/graph/nodes/retrieve.py`

```python
def retrieve_node(state: RAGState) -> dict:
    """Retrieve chunks from Qdrant"""

    from ... import config
    from ...retriever import QdrantRetriever
    from ...hybrid_retriever import QdrantHybridRetriever

    # Select retriever based on config
    if config.RETRIEVAL_MODE == 'hybrid':
        retriever = QdrantHybridRetriever()
    else:
        retriever = QdrantRetriever()

    chunks = retriever.search(state["query"], top_k=config.RETRIEVAL_TOP_K)

    debug_info = {}
    if state.get("debug"):
        debug_info["retrieved_chunks"] = chunks

    return {
        "retrieved_chunks": chunks,
        "debug_info": {**state.get("debug_info", {}), **debug_info}
    }
```

**File:** `chatbot/graph/nodes/rerank.py`

```python
def rerank_node(state: RAGState) -> dict:
    """Rerank chunks using LLM judge"""

    from ... import config
    from ...reranker import LLMJudgeReranker

    # Initialize reranker (same logic as RAGHandler)
    api_key = config.GROQ_API_KEY if config.LLM_PROVIDER == 'groq' else config.OPENAI_API_KEY
    reranker = LLMJudgeReranker(
        api_key=api_key,
        provider=config.LLM_PROVIDER,
        model=config.RERANKER_MODEL
    )

    debug = state.get("debug", False)

    if debug:
        reranked, debug_data = reranker.rerank(
            state["query"],
            state["retrieved_chunks"],
            top_k=config.RERANK_TOP_K,
            debug=True
        )
        return {
            "reranked_chunks": reranked,
            "debug_info": {**state.get("debug_info", {}), **debug_data}
        }
    else:
        reranked = reranker.rerank(
            state["query"],
            state["retrieved_chunks"],
            top_k=config.RERANK_TOP_K
        )
        return {"reranked_chunks": reranked}
```

**File:** `chatbot/graph/nodes/generate.py`

```python
def generate_node(state: RAGState) -> dict:
    """Generate answer from reranked chunks"""

    from ... import config
    from ...generator import ResponseGenerator

    api_key = config.GROQ_API_KEY if config.LLM_PROVIDER == 'groq' else config.OPENAI_API_KEY
    generator = ResponseGenerator(
        api_key=api_key,
        provider=config.LLM_PROVIDER,
        model=config.LLM_MODEL
    )

    result = generator.generate(state["query"], state["reranked_chunks"])

    # Extract cited sources (same logic as RAGHandler._extract_cited_sources)
    import re
    cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+)\]', result['answer']))
    sources = []
    for doc_num in sorted(cited_doc_nums, key=int):
        idx = int(doc_num) - 1
        if 0 <= idx < len(state["reranked_chunks"]):
            chunk = state["reranked_chunks"][idx]
            sources.append({
                'doc': chunk['filename'],
                'page': chunk['page'],
                'url': chunk['source_url']
            })

    return {
        "answer": result['answer'],
        "sources": sources,
        "response_type": "information",
        "action_items": []
    }
```

**File:** `chatbot/graph/nodes/location.py`

```python
def location_node(state: RAGState) -> dict:
    """Return template response for location queries"""

    from ...prompts import LOCATION_SEARCH_TEMPLATE

    return {
        "answer": LOCATION_SEARCH_TEMPLATE,
        "sources": [],
        "response_type": "location_search",
        "action_items": [
            {
                'type': 'link',
                'url': 'https://childcare.hhs.texas.gov/Public/ChildCareSearch',
                'label': 'Search for Childcare Facilities',
                'description': 'Official Texas HHS facility search tool'
            }
        ]
    }
```

---

#### Step 4: Create Conditional Routing

**File:** `chatbot/graph/edges.py`

```python
from typing import Literal

def route_by_intent(state: dict) -> Literal["retrieve", "location"]:
    """Route to appropriate path based on classified intent"""

    if state["intent"] == "location_search":
        return "location"
    else:
        return "retrieve"
```

---

#### Step 5: Build the Graph

**File:** `chatbot/graph/builder.py`

```python
from langgraph.graph import StateGraph, END

from .state import RAGState
from .nodes.classify import classify_node
from .nodes.retrieve import retrieve_node
from .nodes.rerank import rerank_node
from .nodes.generate import generate_node
from .nodes.location import location_node
from .edges import route_by_intent


def build_rag_graph():
    """Build the stateless RAG graph"""

    workflow = StateGraph(RAGState)

    # Add nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)

    # Entry point
    workflow.set_entry_point("classify")

    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "location": "location"
        }
    )

    # Information path: retrieve → rerank → generate → END
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)

    # Location path: location → END
    workflow.add_edge("location", END)

    # Compile (no checkpointer = stateless)
    return workflow.compile()


# Singleton graph instance
_graph = None

def get_graph():
    """Get or create the RAG graph"""
    global _graph
    if _graph is None:
        _graph = build_rag_graph()
    return _graph
```

---

#### Step 6: Add Config Flag

**File:** `chatbot/config.py` (add to existing)

```python
# LangGraph mode
# When False (default): Uses LangGraph with stateless behavior (same as current)
# When True: Enables conversation memory and agentic features
CONVERSATIONAL_MODE = os.getenv("CONVERSATIONAL_MODE", "false").lower() == "true"

# Feature flag to use LangGraph implementation vs legacy
# This allows gradual rollout and easy rollback
USE_LANGGRAPH = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
```

---

#### Step 7: Update Chatbot Entry Point

**File:** `chatbot/chatbot.py` (modified)

```python
from .intent_router import IntentRouter
from . import config
import time


class TexasChildcareChatbot:
    def __init__(self, llm_model=None, reranker_model=None, intent_model=None, provider=None):
        """Initialize chatbot with intent routing and optional custom models"""

        if config.USE_LANGGRAPH:
            # New LangGraph implementation
            from .graph.builder import get_graph
            self.graph = get_graph()
            self.router = None
            print("✓ Chatbot instance created (LangGraph mode)")
        else:
            # Legacy implementation
            self.graph = None
            self.router = IntentRouter(
                llm_model=llm_model,
                reranker_model=reranker_model,
                intent_model=intent_model,
                provider=provider
            )
            print("✓ Chatbot instance created (Legacy mode)")

    def ask(self, question: str, debug: bool = False):
        """Ask a question, returns dict with answer, sources, response_type, action_items, processing_time"""

        start_time = time.time()

        if config.USE_LANGGRAPH:
            # LangGraph path
            initial_state = {
                "query": question,
                "debug": debug,
                "intent": None,
                "retrieved_chunks": [],
                "reranked_chunks": [],
                "answer": None,
                "sources": [],
                "response_type": "",
                "action_items": [],
                "debug_info": {} if debug else None
            }

            final_state = self.graph.invoke(initial_state)

            result = {
                'answer': final_state['answer'],
                'sources': final_state['sources'],
                'response_type': final_state['response_type'],
                'action_items': final_state['action_items']
            }

            if debug:
                result['debug_info'] = final_state.get('debug_info', {})
        else:
            # Legacy path
            result = self.router.route(question)

        result['processing_time'] = round(time.time() - start_time, 2)
        return result
```

---

## Testing Strategy

### Test 1: Unit Tests for Each Node

**File:** `tests/test_graph_nodes.py`

```python
def test_classify_node_information():
    """Test classification of information queries"""
    state = {"query": "What are the income limits for childcare assistance?"}
    result = classify_node(state)
    assert result["intent"] == "information"

def test_classify_node_location():
    """Test classification of location queries"""
    state = {"query": "Find daycare near Austin"}
    result = classify_node(state)
    assert result["intent"] == "location_search"

def test_location_node_returns_template():
    """Test location node returns expected structure"""
    state = {"query": "Find daycare"}
    result = location_node(state)
    assert "childcare.hhs.texas.gov" in result["action_items"][0]["url"]
    assert result["response_type"] == "location_search"
```

### Test 2: Graph Integration Test

**File:** `tests/test_graph_integration.py`

```python
def test_information_path_executes():
    """Test full information query path"""
    graph = build_rag_graph()
    state = {
        "query": "What is PSoC?",
        "debug": False,
        "intent": None,
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "answer": None,
        "sources": [],
        "response_type": "",
        "action_items": [],
        "debug_info": None
    }

    result = graph.invoke(state)

    assert result["answer"] is not None
    assert result["response_type"] == "information"
    assert len(result["answer"]) > 50

def test_location_path_executes():
    """Test location query path"""
    graph = build_rag_graph()
    state = {
        "query": "Where can I find daycare in Houston?",
        # ... initialize all fields
    }

    result = graph.invoke(state)

    assert result["response_type"] == "location_search"
    assert len(result["action_items"]) > 0
```

### Test 3: Parity Test (Legacy vs LangGraph)

**File:** `tests/test_parity.py`

```python
def test_langgraph_matches_legacy():
    """Verify LangGraph produces identical results to legacy"""

    test_queries = [
        "What are the income limits for a family of 4?",
        "How do I apply for childcare assistance?",
        "Find daycare near me",
        "What is the Parent Share of Cost?",
    ]

    # Run with legacy
    os.environ["USE_LANGGRAPH"] = "false"
    legacy_bot = TexasChildcareChatbot()
    legacy_results = [legacy_bot.ask(q) for q in test_queries]

    # Run with LangGraph
    os.environ["USE_LANGGRAPH"] = "true"
    graph_bot = TexasChildcareChatbot()
    graph_results = [graph_bot.ask(q) for q in test_queries]

    # Compare (allow minor timing differences)
    for i, (leg, grp) in enumerate(zip(legacy_results, graph_results)):
        assert leg["response_type"] == grp["response_type"], f"Query {i}: response_type mismatch"
        assert leg["action_items"] == grp["action_items"], f"Query {i}: action_items mismatch"
        # Answer comparison would use LLM judge for semantic similarity
```

### Test 4: Evaluation Suite Regression

```bash
# Run evaluation with legacy
export USE_LANGGRAPH=false
python -m evaluation.run_evaluation --mode hybrid --limit 20
# Save results

# Run evaluation with LangGraph
export USE_LANGGRAPH=true
python -m evaluation.run_evaluation --mode hybrid --limit 20
# Compare scores - should be within ±2%
```

---

## Rollout Plan

### Phase 0a: Implementation (Day 1-2)

1. Add `langgraph` to requirements.txt
2. Create `chatbot/graph/` directory structure
3. Implement state.py
4. Implement all node files
5. Implement edges.py and builder.py
6. Add config flags

### Phase 0b: Testing (Day 2-3)

1. Run unit tests for each node
2. Run integration tests
3. Run parity tests (legacy vs LangGraph)
4. Run full evaluation suite both ways
5. Compare scores - must be within ±2%

### Phase 0c: Validation (Day 3)

1. Manual testing via CLI (`interactive_chat.py`)
2. Web UI testing (frontend + backend)
3. Performance comparison (latency, memory)
4. Code review

### Phase 0d: Merge (Day 4)

1. Merge to main with `USE_LANGGRAPH=false` default
2. Document rollout procedure
3. Enable gradually: dev → staging → prod

---

## Rollback Procedure

If issues discovered:

```bash
# Immediate rollback (no code change)
export USE_LANGGRAPH=false

# Or in config.py
USE_LANGGRAPH = False  # Force legacy mode
```

Legacy code is fully preserved - no modifications to existing files except chatbot.py entry point.

---

## Dependency Management

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | >=0.2.0 | Graph orchestration |

### No Changes To

- `langchain` (already installed)
- `langchain-openai` (already installed)
- `qdrant-client` (already installed)
- `groq` (already installed)
- `openai` (already installed)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LangGraph API changes | Medium | Pin version in requirements.txt |
| Performance regression | Low | Graph is simple linear flow, minimal overhead |
| Debug info structure changes | Low | Map LangGraph state to existing debug format |
| Evaluation score changes | High | Parity testing before merge |

---

## Definition of Done

- [ ] All nodes implemented and unit tested
- [ ] Graph builds and runs without errors
- [ ] Legacy mode unchanged when `USE_LANGGRAPH=false`
- [ ] Parity tests pass (same results as legacy)
- [ ] Evaluation scores within ±2% of baseline
- [ ] Web UI works with LangGraph mode
- [ ] Documentation updated
- [ ] Code reviewed and merged

---

## Next Steps (Post Phase 0)

Once Phase 0 is validated:

1. **Phase 1:** Add checkpointer (conversation memory)
2. **Phase 2:** Add query rewriter node
3. **Phase 3:** Add intelligent router
4. **Phase 4-6:** See agentic-rag-design-2025-11-26.md
