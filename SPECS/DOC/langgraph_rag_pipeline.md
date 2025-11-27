# LangGraph RAG Pipeline

Mermaid diagram showing the current graph flow for the Texas Childcare Chatbot.

## Graph Diagram

```mermaid
flowchart TD
    START((START)) --> classify[classify_node<br/><i>Intent Classification</i>]

    classify -->|route_by_intent| decision{intent?}

    decision -->|"information"| retrieve[retrieve_node<br/><i>Qdrant Vector Search</i>]
    decision -->|"location_search"| location[location_node<br/><i>Template Response</i>]

    retrieve --> rerank[rerank_node<br/><i>LLM Relevance Scoring</i>]
    rerank --> generate[generate_node<br/><i>Answer Generation</i>]

    generate --> END1((END))
    location --> END2((END))

    subgraph RAGState
        direction LR
        query[query]
        intent[intent]
        retrieved_chunks[retrieved_chunks]
        reranked_chunks[reranked_chunks]
        answer[answer]
        sources[sources]
    end

    style START fill:#2d5a27,color:#fff
    style END1 fill:#8b0000,color:#fff
    style END2 fill:#8b0000,color:#fff
    style decision fill:#4a4a4a,color:#fff
    style classify fill:#1e3a5f,color:#fff
    style retrieve fill:#1e3a5f,color:#fff
    style rerank fill:#1e3a5f,color:#fff
    style generate fill:#1e3a5f,color:#fff
    style location fill:#5f3a1e,color:#fff
```

## Graph Structure

| Path | Flow | Use Case |
|------|------|----------|
| **Information** | `START → classify → retrieve → rerank → generate → END` | Policy questions, eligibility queries |
| **Location** | `START → classify → location → END` | "Find childcare near me" |

## Nodes

| Node | File | Description |
|------|------|-------------|
| `classify` | `chatbot/graph/nodes/classify.py` | LLM intent classification (information vs location_search) |
| `retrieve` | `chatbot/graph/nodes/retrieve.py` | Qdrant hybrid/dense vector search |
| `rerank` | `chatbot/graph/nodes/rerank.py` | LLM-based relevance scoring |
| `generate` | `chatbot/graph/nodes/generate.py` | Answer generation with citations |
| `location` | `chatbot/graph/nodes/location.py` | Template response with HHS facility search link |

## State (RAGState)

Defined in `chatbot/graph/state.py`:

```python
class RAGState(TypedDict):
    # Input
    query: str                              # User's question
    debug: bool                             # Enable debug output

    # Routing
    intent: Literal["information", "location_search"] | None

    # Retrieval (information path)
    retrieved_chunks: list[dict]            # From Qdrant
    reranked_chunks: list[dict]             # After LLM scoring

    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]
    debug_info: dict | None
```

## Conditional Routing

Defined in `chatbot/graph/edges.py`:

- `route_by_intent(state)` returns `"retrieve"` or `"location"` based on `state["intent"]`

## Key Files

| File | Purpose |
|------|---------|
| `chatbot/graph/builder.py` | Graph construction with `StateGraph` |
| `chatbot/graph/state.py` | `RAGState` TypedDict definition |
| `chatbot/graph/edges.py` | Conditional routing logic |
| `chatbot/graph/nodes/*.py` | Individual node implementations |
