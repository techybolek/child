# LangGraph Conversational RAG Pipeline

Mermaid diagram showing the proposed conversational graph flow with multi-turn memory.

## Graph Diagram

```mermaid
flowchart TD
    START((START)) --> reformulate[reformulate_node<br/><i>Query Rewriting</i>]

    reformulate --> classify[classify_node<br/><i>Intent Classification</i>]

    classify -->|route_by_intent| decision{intent?}

    decision -->|"information"| retrieve[retrieve_node<br/><i>Qdrant Vector Search</i>]
    decision -->|"location_search"| location[location_node<br/><i>Template Response</i>]
    decision -->|"clarification"| clarify[clarify_node<br/><i>Ask for Details</i>]

    retrieve --> rerank[rerank_node<br/><i>LLM Relevance Scoring</i>]
    rerank --> generate[generate_node<br/><i>Answer Generation</i>]

    generate --> END1((END))
    location --> END2((END))
    clarify --> END3((END))

    style START fill:#2d5a27,color:#fff
    style END1 fill:#8b0000,color:#fff
    style END2 fill:#8b0000,color:#fff
    style END3 fill:#8b0000,color:#fff
    style decision fill:#4a4a4a,color:#fff
    style reformulate fill:#5f1e5f,color:#fff
    style classify fill:#1e3a5f,color:#fff
    style retrieve fill:#1e3a5f,color:#fff
    style rerank fill:#1e3a5f,color:#fff
    style generate fill:#1e3a5f,color:#fff
    style location fill:#5f3a1e,color:#fff
    style clarify fill:#3a5f1e,color:#fff
```

## Comparison: Stateless vs Conversational

```mermaid
flowchart LR
    subgraph Current["Current (Stateless)"]
        direction TB
        A1[Query] --> A2[Classify] --> A3[Retrieve] --> A4[Rerank] --> A5[Generate] --> A6[Response]
    end
    
    subgraph Proposed["Proposed (Conversational)"]
        direction TB
        B0[("Memory<br/>thread_id")] -.-> B1
        B1[Query] --> B2[REFORMULATE] --> B3[Classify] --> B4[Retrieve] --> B5[Rerank] --> B6[Generate] --> B7[Response]
        B7 -.-> B0
    end
    
    style B2 fill:#5f1e5f,color:#fff
    style B0 fill:#2a4a6a,color:#fff
```

## Graph Structure

| Path | Flow | Use Case |
|------|------|----------|
| **Information** | `START → reformulate → classify → retrieve → rerank → generate → END` | Policy questions, eligibility queries |
| **Location** | `START → reformulate → classify → location → END` | "Find childcare near me" |
| **Clarification** | `START → reformulate → classify → clarify → END` | Ambiguous requests needing more info |

## Nodes

| Node | File | Description |
|------|------|-------------|
| `reformulate` | `chatbot/graph/nodes/reformulate.py` | **NEW** - Rewrites context-dependent queries to standalone |
| `classify` | `chatbot/graph/nodes/classify.py` | LLM intent classification (information, location_search, clarification) |
| `retrieve` | `chatbot/graph/nodes/retrieve.py` | Qdrant hybrid/dense vector search using `reformulated_query` |
| `rerank` | `chatbot/graph/nodes/rerank.py` | LLM-based relevance scoring with conversation context |
| `generate` | `chatbot/graph/nodes/generate.py` | Answer generation with citations |
| `location` | `chatbot/graph/nodes/location.py` | Template response with HHS facility search link |
| `clarify` | `chatbot/graph/nodes/clarify.py` | **NEW** - Asks user for missing information |

## State (ConversationalRAGState)

Defined in `chatbot/graph/state.py`:

```python
from typing import TypedDict, Literal, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ConversationalRAGState(TypedDict):
    # Conversation history (accumulated via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Current turn
    query: str                              # Original user query
    reformulated_query: str | None          # History-aware standalone query
    
    # Routing
    intent: Literal["information", "location_search", "clarification"] | None
    needs_clarification: bool
    
    # Retrieval (information path)
    retrieved_chunks: list[dict]            # From Qdrant
    reranked_chunks: list[dict]             # After LLM scoring
    
    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]
    
    # Debug
    debug: bool
    debug_info: dict | None
```

## Memory Architecture

```mermaid
flowchart TB
    subgraph Checkpointer["InMemorySaver / PostgresSaver"]
        T1["thread_id: abc-123"]
        T2["thread_id: def-456"]
        T3["thread_id: ghi-789"]
    end
    
    subgraph Thread1["Conversation abc-123"]
        M1[Turn 1: User + AI]
        M2[Turn 2: User + AI]
        M3[Turn 3: User + AI]
    end
    
    T1 --> Thread1
    
    style T1 fill:#2a4a6a,color:#fff
    style T2 fill:#4a4a4a,color:#fff
    style T3 fill:#4a4a4a,color:#fff
```

## Query Reformulation Flow

```mermaid
flowchart LR
    subgraph Turn1["Turn 1"]
        Q1["What is CCS?"]
        R1["CCS is the Child Care Services program..."]
    end
    
    subgraph Turn2["Turn 2"]
        Q2["How do I apply for it?"]
        RF["reformulate_node"]
        Q2R["How do I apply for the Child Care Services (CCS) program?"]
    end
    
    Q1 --> R1
    R1 -.->|context| RF
    Q2 --> RF --> Q2R
    Q2R --> Retrieve
    
    style RF fill:#5f1e5f,color:#fff
    style Q2R fill:#1e5f3a,color:#fff
```

## Conditional Routing

Defined in `chatbot/graph/edges.py`:

```python
def route_by_intent(state: ConversationalRAGState) -> str:
    """Route based on classified intent."""
    intent = state.get("intent")
    
    if state.get("needs_clarification"):
        return "clarify"
    elif intent == "location_search":
        return "location"
    else:
        return "retrieve"
```

## Key Files

| File | Purpose |
|------|---------|
| `chatbot/graph/builder.py` | Graph construction with checkpointer |
| `chatbot/graph/state.py` | `ConversationalRAGState` TypedDict |
| `chatbot/graph/edges.py` | Conditional routing logic |
| `chatbot/graph/nodes/reformulate.py` | **NEW** - Query reformulation |
| `chatbot/graph/nodes/clarify.py` | **NEW** - Clarification requests |
| `chatbot/memory.py` | **NEW** - Memory manager |

## Usage

```python
from chatbot import TexasChildcareChatbot

bot = TexasChildcareChatbot()

# Turn 1
r1 = bot.ask("What is the income limit for CCS?", thread_id="conv-123")

# Turn 2 - uses context from Turn 1
r2 = bot.ask("What about for a family of 4?", thread_id="conv-123")
# reformulated_query: "What is the income limit for CCS for a family of 4?"

# Turn 3 - continues context
r3 = bot.ask("How do I apply?", thread_id="conv-123")
# reformulated_query: "How do I apply for CCS?"

# New conversation
r4 = bot.ask("Where can I find daycare?", thread_id="conv-456")
```
