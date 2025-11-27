# Agentic RAG Graph Design

Mermaid diagram for the proposed conversational chatbot with agentic capabilities.

## Full Agentic Graph (Conversational Mode)

```mermaid
flowchart TD
    START((START)) --> router[ROUTER<br/><i>Analyze query + history</i>]

    router -->|route_after_router| route_decision{route_decision?}

    route_decision -->|DIRECT_ANSWER| generate[GENERATE<br/><i>Use prior context</i>]
    route_decision -->|RETRIEVE| retrieve[RETRIEVE<br/><i>Vector search</i>]
    route_decision -->|REWRITE_THEN_RETRIEVE| rewrite[REWRITE<br/><i>Expand query</i>]
    route_decision -->|ASK_CLARIFICATION| clarify[CLARIFY<br/><i>Human-in-the-loop</i>]
    route_decision -->|LOCATION_SEARCH| location[LOCATION<br/><i>Facility finder</i>]

    rewrite --> retrieve
    clarify -->|user responds| retrieve

    retrieve --> grade[GRADE<br/><i>Score relevance</i>]

    grade -->|route_after_grading| grade_decision{relevant_count?}

    grade_decision -->|"≥3 relevant"| generate
    grade_decision -->|"<3 & retry<2"| rewrite_retry[REWRITE<br/><i>Retry query</i>]
    grade_decision -->|"<3 & retry≥2"| generate_caveat[GENERATE<br/><i>Best effort + caveat</i>]

    rewrite_retry --> retrieve

    generate --> validate[VALIDATE<br/><i>Check groundedness</i>]
    generate_caveat --> validate

    validate -->|route_after_validation| validate_decision{grounded?}

    validate_decision -->|"yes"| END1((END))
    validate_decision -->|"no & retry<2"| rewrite_final[REWRITE<br/><i>Different angle</i>]
    validate_decision -->|"no & retry≥2"| clarify_final[CLARIFY<br/><i>Give up, ask user</i>]

    rewrite_final --> retrieve
    clarify_final -->|user responds| retrieve

    location --> END2((END))

    subgraph Legend
        direction LR
        L1[Decision Node]
        L2[Processing Node]
        L3[Human Interrupt]
    end

    style START fill:#2d5a27,color:#fff
    style END1 fill:#8b0000,color:#fff
    style END2 fill:#8b0000,color:#fff
    style route_decision fill:#4a4a4a,color:#fff
    style grade_decision fill:#4a4a4a,color:#fff
    style validate_decision fill:#4a4a4a,color:#fff
    style router fill:#1e3a5f,color:#fff
    style retrieve fill:#1e3a5f,color:#fff
    style rewrite fill:#1e3a5f,color:#fff
    style rewrite_retry fill:#1e3a5f,color:#fff
    style rewrite_final fill:#1e3a5f,color:#fff
    style grade fill:#1e3a5f,color:#fff
    style generate fill:#1e3a5f,color:#fff
    style generate_caveat fill:#1e3a5f,color:#fff
    style validate fill:#1e3a5f,color:#fff
    style clarify fill:#8b4513,color:#fff
    style clarify_final fill:#8b4513,color:#fff
    style location fill:#5f3a1e,color:#fff
```

## Simple Mode Graph (Stateless - Current Behavior)

```mermaid
flowchart TD
    START((START)) --> classify[CLASSIFY<br/><i>Intent classification</i>]

    classify --> intent_decision{intent?}

    intent_decision -->|information| retrieve[RETRIEVE<br/><i>Vector search</i>]
    intent_decision -->|location_search| location[LOCATION<br/><i>Template response</i>]

    retrieve --> rerank[RERANK<br/><i>LLM scoring</i>]
    rerank --> generate[GENERATE<br/><i>Answer + citations</i>]

    generate --> END1((END))
    location --> END2((END))

    style START fill:#2d5a27,color:#fff
    style END1 fill:#8b0000,color:#fff
    style END2 fill:#8b0000,color:#fff
    style intent_decision fill:#4a4a4a,color:#fff
    style classify fill:#1e3a5f,color:#fff
    style retrieve fill:#1e3a5f,color:#fff
    style rerank fill:#1e3a5f,color:#fff
    style generate fill:#1e3a5f,color:#fff
    style location fill:#5f3a1e,color:#fff
```

## Mode Comparison

| Aspect | Simple Mode (Stateless) | Agentic Mode (Conversational) |
|--------|------------------------|------------------------------|
| **Memory** | None | Checkpointer (thread_id) |
| **Query Handling** | As-is | Rewrite ambiguous queries |
| **Retrieval** | Always retrieve | Skip if prior context sufficient |
| **Quality Control** | Single pass | Grade → Retry → Validate |
| **Failure Handling** | Best effort | Clarification loop |
| **Config Flag** | `CONVERSATIONAL_MODE=false` | `CONVERSATIONAL_MODE=true` |

## Router Decisions

| Decision | Condition | Next Node |
|----------|-----------|-----------|
| `DIRECT_ANSWER` | Follow-up answerable from prior context | generate |
| `RETRIEVE` | New topic or factual question | retrieve |
| `REWRITE_THEN_RETRIEVE` | Ambiguous query, uses pronouns | rewrite |
| `ASK_CLARIFICATION` | Genuinely unclear | clarify |
| `LOCATION_SEARCH` | Facility finding request | location |

## State Definition (AgentState)

```python
class AgentState(TypedDict):
    # Conversation
    messages: list[BaseMessage]           # Full history

    # Current turn
    original_query: str
    rewritten_query: str | None

    # Retrieval
    retrieved_docs: list[Document]
    doc_relevance_scores: list[float]

    # Generation
    draft_answer: str | None
    final_answer: str | None
    sources: list[dict]

    # Control flow
    route_decision: str
    retry_count: int
    needs_clarification: str | None
    confidence: float
```

## Implementation Phases

| Phase | Component | Status |
|-------|-----------|--------|
| 0 | Migrate to LangGraph (stateless) | ✅ Done |
| 1 | Add checkpointer (memory) | Planned |
| 2 | Add query rewriter | Planned |
| 3 | Add router | Planned |
| 4 | Add document grader | Planned |
| 5 | Add validator | Planned |
| 6 | Add clarification (HITL) | Planned |

## Key Files

| File | Purpose |
|------|---------|
| `chatbot/graph/builder.py` | Graph construction |
| `chatbot/graph/state.py` | State definition |
| `chatbot/graph/edges.py` | Conditional routing |
| `chatbot/graph/nodes/*.py` | Node implementations |
| `chatbot/prompts/agentic/*.py` | New prompts (planned) |
