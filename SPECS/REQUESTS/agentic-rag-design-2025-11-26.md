# Agentic RAG Design for Texas Childcare Chatbot

**Date:** 2025-11-26
**Status:** Design/Research
**Priority:** High

## Problem Statement

The current chatbot is **100% stateless**. Each question is processed in isolation:
- No conversation history passed to retriever
- No memory of previous questions in the prompt
- Intent classification ignores prior context
- Frontend stores message history but never sends it to backend

This causes failures on follow-up questions like:
- "What about family of 5?" (after income limit question)
- "Can I use it on my phone?" (after discussing KinderConnect)
- "Is that more than 45%?" (after PSoC discussion)

## Proposed Solution: Agentic RAG

Instead of a fixed pipeline (`retrieve → rerank → generate`), implement an **agent that reasons about what to do next** at each step.

## Design Decision: LangGraph for Both Modes

**Key decision:** Use LangGraph as the unified framework for both stateless and conversational modes.

### Why Single Codebase with Feature Flag

| Approach | Pros | Cons |
|----------|------|------|
| **Dual systems** (keep existing + LangGraph for conversational) | No migration risk | Two codebases to maintain, divergent behavior |
| **LangGraph for both** (recommended) | Single codebase, consistent behavior, cleaner long-term | Initial migration effort |

### How It Works

```python
# chatbot/config.py
CONVERSATIONAL_MODE = os.getenv("CONVERSATIONAL_MODE", "false").lower() == "true"
```

**When `CONVERSATIONAL_MODE=false` (default):**
- Simple linear graph: `retrieve → rerank → generate`
- No checkpointer (stateless)
- Behaves identically to current system
- No router, no query rewriting, no clarification

**When `CONVERSATIONAL_MODE=true`:**
- Full agentic graph with router, rewriter, grader, validator, clarification
- Checkpointer enabled (conversation memory)
- All advanced features active

### Simple Mode Graph (Stateless)

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌─────────┐
│  START  │ ──→ │RETRIEVE │ ──→ │ RERANK   │ ──→ │GENERATE │ ──→ END
└─────────┘     └─────────┘     └──────────┘     └─────────┘
```

This is the current workflow, just implemented in LangGraph for consistency.

### Conversational Mode Graph (Full Agentic)

See "Complete Graph Visualization" section below for full diagram.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENTIC RAG                                 │
│                                                                     │
│   User Query + Conversation History                                 │
│              ↓                                                      │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    ROUTER AGENT                              │  │
│   │  "What's the best way to handle this query?"                 │  │
│   │                                                              │  │
│   │  Decisions:                                                  │  │
│   │  • DIRECT_ANSWER - I already have enough context             │  │
│   │  • RETRIEVE - Need to search vector DB                       │  │
│   │  • REWRITE_THEN_RETRIEVE - Query is ambiguous, rewrite first │  │
│   │  • ASK_CLARIFICATION - Need more info from user              │  │
│   │  • LOCATION_SEARCH - Route to facility finder                │  │
│   └─────────────────────────────────────────────────────────────┘  │
│              ↓                                                      │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │              EXECUTION + SELF-CORRECTION                     │  │
│   │                                                              │  │
│   │  After retrieval, grade documents:                           │  │
│   │  • RELEVANT → Generate answer                                │  │
│   │  • NOT_RELEVANT → Rewrite query and retry                    │  │
│   │  • PARTIAL → Generate with caveat OR ask clarification       │  │
│   │                                                              │  │
│   │  After generation, validate:                                 │  │
│   │  • GROUNDED → Return to user                                 │  │
│   │  • HALLUCINATING → Regenerate with stricter prompt           │  │
│   │  • OFF_TOPIC → Rewrite and re-retrieve                       │  │
│   └─────────────────────────────────────────────────────────────┘  │
│              ↓                                                      │
│   Response (with sources, confidence, action items)                │
└─────────────────────────────────────────────────────────────────────┘
```

## State Definition

```python
class AgentState(TypedDict):
    # Conversation
    messages: list[BaseMessage]           # Full conversation history

    # Current turn
    original_query: str                   # User's raw input
    rewritten_query: str | None           # Clarified/expanded query

    # Retrieval
    retrieved_docs: list[Document]        # From vector DB
    doc_relevance_scores: list[float]     # Grading results

    # Generation
    draft_answer: str | None              # Before validation
    final_answer: str | None              # After validation
    sources: list[dict]                   # Citations

    # Control flow
    route_decision: str                   # Router's choice
    retry_count: int                      # Prevent infinite loops
    needs_clarification: str | None       # Question to ask user
    confidence: float                     # Answer confidence
```

## Decision Nodes

### 1. Router Node

Analyzes query + conversation and decides the path:

```python
def router_node(state: AgentState) -> dict:
    """Decide how to handle this query."""

    decision = llm.invoke(ROUTER_PROMPT.format(
        conversation=format_conversation(state["messages"]),
        query=state["original_query"],
        has_prior_context=len(state["retrieved_docs"]) > 0
    ))

    return {"route_decision": decision.route}
```

**Router decisions:**

| Decision | When to use | Example |
|----------|-------------|---------|
| `DIRECT_ANSWER` | Follow-up that can be answered from prior context | "What about for 2 children?" (after discussing PSoC) |
| `RETRIEVE` | New topic or specific factual question | "What are the income limits?" |
| `REWRITE_THEN_RETRIEVE` | Ambiguous or uses pronouns | "What about that?" |
| `ASK_CLARIFICATION` | Genuinely unclear | "Help me with the program" (which program?) |
| `LOCATION_SEARCH` | Facility finding | "Find daycare near Austin" |

### 2. Query Rewriter Node

Expands ambiguous queries using conversation context:

```python
def rewrite_node(state: AgentState) -> dict:
    """Rewrite query to be self-contained."""

    rewritten = llm.invoke(REWRITE_PROMPT.format(
        conversation=format_last_n_turns(state["messages"], n=3),
        query=state["original_query"]
    ))

    return {"rewritten_query": rewritten.query}
```

**Example transformations:**

| Original | Context | Rewritten |
|----------|---------|-----------|
| "What about family of 5?" | Was discussing income limits | "What is the income eligibility limit for a family of 5 in BCY 2026?" |
| "Can I use it on my phone?" | Discussed KinderConnect | "Can I use KinderConnect on my mobile phone?" |
| "Is that more than 45%?" | Discussed PSoC at 35% SMI | "Is the Parent Share of Cost at 35% SMI higher or lower than at 45% SMI?" |

### 3. Retrieval Node

Searches vector DB with best available query:

```python
def retrieve_node(state: AgentState) -> dict:
    """Retrieve relevant documents."""

    query = state["rewritten_query"] or state["original_query"]
    docs = retriever.search(query, top_k=20)

    return {"retrieved_docs": docs}
```

### 4. Document Grader Node

Assesses if retrieved docs can answer the question:

```python
def grade_documents_node(state: AgentState) -> dict:
    """Grade document relevance."""

    query = state["rewritten_query"] or state["original_query"]
    scores = []

    for doc in state["retrieved_docs"]:
        score = llm.invoke(GRADING_PROMPT.format(
            question=query,
            document=doc.page_content
        ))
        scores.append(score.relevance)

    return {"doc_relevance_scores": scores}
```

### 5. Generator Node

Creates answer from relevant documents:

```python
def generate_node(state: AgentState) -> dict:
    """Generate answer from documents."""

    relevant_docs = [
        doc for doc, score in zip(state["retrieved_docs"], state["doc_relevance_scores"])
        if score > 0.7
    ]

    answer = llm.invoke(GENERATION_PROMPT.format(
        conversation=format_conversation(state["messages"]),
        question=state["original_query"],
        context=format_documents(relevant_docs)
    ))

    return {
        "draft_answer": answer.content,
        "sources": extract_sources(relevant_docs)
    }
```

### 6. Answer Validator Node

Checks for hallucinations and relevance:

```python
def validate_node(state: AgentState) -> dict:
    """Validate answer quality."""

    validation = llm.invoke(VALIDATION_PROMPT.format(
        question=state["original_query"],
        documents=format_documents(state["retrieved_docs"]),
        answer=state["draft_answer"]
    ))

    if validation.is_grounded and validation.answers_question:
        return {
            "final_answer": state["draft_answer"],
            "confidence": validation.confidence
        }
    else:
        return {
            "final_answer": None,
            "confidence": 0.0
        }
```

### 7. Clarification Node (Human-in-the-Loop)

Asks user for more information:

```python
def clarification_node(state: AgentState) -> dict:
    """Ask user for clarification."""

    question = llm.invoke(CLARIFICATION_PROMPT.format(
        conversation=format_conversation(state["messages"]),
        query=state["original_query"]
    ))

    # This triggers an interrupt - execution pauses until user responds
    user_response = interrupt({
        "type": "clarification_needed",
        "question": question.clarifying_question,
        "options": question.suggested_options  # Optional multiple choice
    })

    return {
        "original_query": f"{state['original_query']} - User clarified: {user_response}",
        "messages": state["messages"] + [
            AIMessage(content=question.clarifying_question),
            HumanMessage(content=user_response)
        ]
    }
```

## Conditional Routing (The "Agentic" Part)

```python
# After router decides
def route_after_router(state: AgentState) -> str:
    decision = state["route_decision"]

    if decision == "DIRECT_ANSWER":
        return "generate"  # Skip retrieval, use prior context
    elif decision == "RETRIEVE":
        return "retrieve"
    elif decision == "REWRITE_THEN_RETRIEVE":
        return "rewrite"
    elif decision == "ASK_CLARIFICATION":
        return "clarify"
    elif decision == "LOCATION_SEARCH":
        return "location_handler"

# After grading documents
def route_after_grading(state: AgentState) -> str:
    relevant_count = sum(1 for s in state["doc_relevance_scores"] if s > 0.7)

    if relevant_count >= 3:
        return "generate"  # Enough relevant docs
    elif state["retry_count"] < 2:
        return "rewrite"   # Try rephrasing query
    else:
        return "generate_with_caveat"  # Best effort answer

# After validation
def route_after_validation(state: AgentState) -> str:
    if state["final_answer"]:
        return END
    elif state["retry_count"] < 2:
        return "rewrite"   # Try again with different query
    else:
        return "clarify"   # Give up, ask user
```

## Complete Graph Visualization

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         ↓
                    ┌─────────┐
                    │ ROUTER  │
                    └────┬────┘
                         ↓
         ┌───────────────┼───────────────┬─────────────────┐
         ↓               ↓               ↓                 ↓
    ┌─────────┐    ┌─────────┐    ┌───────────┐    ┌────────────┐
    │ REWRITE │    │RETRIEVE │    │ CLARIFY   │    │ LOCATION   │
    └────┬────┘    └────┬────┘    │ (interrupt)│    │ HANDLER    │
         │              ↓         └─────┬─────┘    └──────┬─────┘
         │         ┌─────────┐          │                 │
         └────────→│  GRADE  │←─────────┘                 │
                   └────┬────┘                            │
                        ↓                                 │
              ┌─────────┴─────────┐                       │
              ↓                   ↓                       │
         ┌─────────┐        ┌───────────┐                 │
         │GENERATE │        │  REWRITE  │                 │
         └────┬────┘        │  (retry)  │                 │
              ↓             └───────────┘                 │
         ┌─────────┐                                      │
         │VALIDATE │                                      │
         └────┬────┘                                      │
              ↓                                           │
         ┌─────────┐                                      │
         │   END   │←─────────────────────────────────────┘
         └─────────┘
```

## Conversation Memory with LangGraph Checkpointing

```python
from langgraph.checkpoint.memory import InMemorySaver
# Or for production:
# from langgraph.checkpoint.redis import RedisSaver

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

# Each conversation has a thread_id
config = {"configurable": {"thread_id": "user-session-123"}}

# First message
graph.invoke({"messages": [HumanMessage("What's the income limit for family of 4?")]}, config)

# Follow-up automatically has conversation history
graph.invoke({"messages": [HumanMessage("What about family of 5?")]}, config)
```

The checkpointer automatically:
- Stores full conversation state after each turn
- Loads prior state when same `thread_id` is used
- Enables "time travel" to any prior checkpoint

## Testing Strategy

### Level 1: Unit Test Each Decision Node

```python
# Test router decisions
test_cases = [
    {
        "messages": [],
        "query": "What's the income limit?",
        "expected_route": "RETRIEVE"
    },
    {
        "messages": [
            HumanMessage("What's the income limit for family of 4?"),
            AIMessage("$92,041 annually...")
        ],
        "query": "What about family of 5?",
        "expected_route": "REWRITE_THEN_RETRIEVE"
    },
    {
        "messages": [
            HumanMessage("What's the PSoC for family of 4 at 35% SMI?"),
            AIMessage("$135/month...")
        ],
        "query": "Is that for one child or two?",
        "expected_route": "DIRECT_ANSWER"
    },
    {
        "messages": [],
        "query": "Help me",
        "expected_route": "ASK_CLARIFICATION"
    }
]
```

### Level 2: Test Query Rewriting Quality

```python
rewrite_tests = [
    {
        "conversation": [
            ("user", "What's the income limit for family of 4?"),
            ("assistant", "$92,041 annually...")
        ],
        "query": "What about family of 5?",
        "rewritten_must_contain": ["income", "eligibility", "family of 5", "BCY 2026"]
    },
    {
        "conversation": [
            ("user", "How do I record attendance?"),
            ("assistant", "Use KinderSign tablet...")
        ],
        "query": "What if it's offline?",
        "rewritten_must_contain": ["KinderSign", "tablet", "offline"]
    }
]
```

### Level 3: Multi-Turn Conversation Tests

Create `QUESTIONS/conversational/` with multi-turn scenarios:

```markdown
# Conversational Test: Income Limit Deep Dive

## Turn 1
**User:** What's the income limit for a family of 4?
**Expected Route:** RETRIEVE
**Expected Answer Contains:** $92,041, annual, BCY 2026

## Turn 2
**User:** What about family of 5?
**Expected Route:** REWRITE_THEN_RETRIEVE
**Rewritten Query Contains:** income eligibility, family of 5
**Expected Answer Contains:** $106,768

## Turn 3
**User:** And what would my PSoC be at that income?
**Expected Route:** REWRITE_THEN_RETRIEVE
**Expected Answer Contains:** 85% SMI, maximum PSoC

## Turn 4
**User:** Is that monthly or weekly?
**Expected Route:** DIRECT_ANSWER
```

### Level 4: End-to-End Trajectory Testing

```python
def test_trajectory(conversation_turns, expected_trajectories):
    """Test that agent takes expected path through graph."""

    config = {"configurable": {"thread_id": "test-123"}}

    for i, (user_msg, expected_nodes) in enumerate(zip(conversation_turns, expected_trajectories)):
        visited_nodes = []

        for event in graph.stream({"messages": [HumanMessage(user_msg)]}, config):
            visited_nodes.append(event.get("node_name"))

        assert visited_nodes == expected_nodes, f"Turn {i}: Expected {expected_nodes}, got {visited_nodes}"
```

### Level 5: Clarification Flow Testing

```python
def test_clarification_flow():
    config = {"configurable": {"thread_id": "clarify-test"}}

    # Ambiguous query should trigger clarification
    result = graph.invoke({"messages": [HumanMessage("Help me with the program")]}, config)

    assert result.get("__interrupt__") is not None
    assert "clarification" in result["__interrupt__"][0].value["type"]

    # Resume with clarification
    from langgraph.types import Command
    result = graph.invoke(
        Command(resume="I need help with CCS eligibility"),
        config
    )

    assert result["final_answer"] is not None
```

### Level 6: Regression Testing Against Current System

```python
def test_agentic_vs_baseline():
    """Compare agentic RAG against current stateless system."""

    test_questions = load_qa_pairs("QUESTIONS/pdfs/")

    baseline_scores = []
    agentic_scores = []

    for qa in test_questions:
        baseline_answer = current_chatbot.ask(qa.question)
        baseline_score = judge.score(qa.expected, baseline_answer)
        baseline_scores.append(baseline_score)

        agentic_answer = agentic_graph.invoke(...)
        agentic_score = judge.score(qa.expected, agentic_answer)
        agentic_scores.append(agentic_score)

    # Agentic should be >= baseline on single-turn questions
    assert mean(agentic_scores) >= mean(baseline_scores) * 0.95
```

## Implementation Phases

| Phase | Component | Risk | Benefit |
|-------|-----------|------|---------|
| **0** | **Migrate current workflow to LangGraph** | Low | Foundation - same behavior, new framework |
| 1 | Add conversation memory (checkpointer) | Low | Foundation for conversational features |
| 2 | Add query rewriter | Low | Improves follow-up handling |
| 3 | Add router | Medium | Enables intelligent path selection |
| 4 | Add document grader | Medium | Enables retry logic |
| 5 | Add validator | Medium | Prevents bad answers |
| 6 | Add clarification (human-in-the-loop) | High | Handles ambiguity gracefully |

### Phase 0: Migration to LangGraph (No Feature Change)

**Goal:** Reimplement current stateless workflow in LangGraph without changing behavior.

```python
def build_simple_graph():
    """Current workflow as LangGraph - no conversational features."""
    workflow = StateGraph(SimpleState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)

    # No checkpointer = stateless
    return workflow.compile()
```

**Validation:** Run existing evaluation suite - scores should be identical.

### Phase 1+: Add Conversational Features Behind Flag

```python
def build_graph():
    if config.CONVERSATIONAL_MODE:
        return build_agentic_graph()  # Full featured
    else:
        return build_simple_graph()   # Current behavior
```

Each phase is independently testable and deployable. Users can opt-in to conversational mode when ready.

## Prompt Design Strategy

### Prompts Required (6)

| Prompt | Purpose | Output Type | Base From |
|--------|---------|-------------|-----------|
| **Router** | Classify query into 5 categories | `RouteDecision` enum | New (adapt from intent_classification_prompt.py) |
| **Query Rewriter** | Expand ambiguous query using conversation | `RewrittenQuery` string | New |
| **Document Grader** | Score chunk relevance 0-1 | `RelevanceScore` float | New |
| **Generator** | Answer with citations | `Answer` string | Existing (response_generation_prompt.py) - add conversation context |
| **Validator** | Check groundedness + answers question | `ValidationResult` bool + confidence | New |
| **Clarification** | Generate clarifying question + options | `ClarificationRequest` | New |

### Design Principles

1. **Structured Output** - Each prompt returns a Pydantic model for reliable parsing:
   ```python
   class RouteDecision(BaseModel):
       route: Literal["DIRECT_ANSWER", "RETRIEVE", "REWRITE_THEN_RETRIEVE", "ASK_CLARIFICATION", "LOCATION_SEARCH"]
       reasoning: str  # For debugging/logging
   ```

2. **Few-Shot Examples** - Include 2-3 examples per prompt derived from real Q&A patterns in `QUESTIONS/pdfs/`

3. **Adapt Existing Prompts** - Start from `chatbot/prompts/` where possible:
   - `intent_classification_prompt.py` → Router (expand categories)
   - `response_generation_prompt.py` → Generator (add conversation context)

### Tuning Strategy

**Per-prompt evaluation sets:**

| Prompt | Test Cases | Source |
|--------|------------|--------|
| Router | 20 cases | Hand-curated from Q&A files + edge cases |
| Query Rewriter | 15 cases | Multi-turn scenarios from `QUESTIONS/conversational/` |
| Document Grader | 30 cases | Sample chunks + questions with known relevance |
| Generator | Existing eval | Use current evaluation system |
| Validator | 20 cases | Good answers + known hallucinations |
| Clarification | 10 cases | Ambiguous queries |

**Iteration loop:**
1. Create test cases with expected outputs
2. Run prompt → compare to expected
3. Adjust prompt wording/examples
4. Repeat until accuracy > 90%
5. Integration test full graph

### Prompt File Structure

```
chatbot/prompts/
├── intent_classification_prompt.py  # Existing
├── response_generation_prompt.py    # Existing (modify)
├── agentic/                         # New directory
│   ├── router_prompt.py
│   ├── query_rewriter_prompt.py
│   ├── document_grader_prompt.py
│   ├── validator_prompt.py
│   └── clarification_prompt.py
```

## Technology Stack

- **Framework:** LangGraph (graph-based agent orchestration)
- **Checkpointing:** InMemorySaver (dev) / RedisSaver (prod)
- **LLM:** GROQ (fast inference) or OpenAI
- **Vector DB:** Qdrant (existing)

## References

- [Top 7 Agentic RAG System Architectures](https://www.analyticsvidhya.com/blog/2025/01/agentic-rag-system-architectures/)
- [Agentic Decision-Tree RAG with Query Routing](https://www.marktechpost.com/2025/10/27/how-to-build-an-agentic-decision-tree-rag-system-with-intelligent-query-routing-self-checking-and-iterative-refinement/)
- [IBM: What is Agentic RAG?](https://www.ibm.com/think/topics/agentic-rag)
- [Comprehensive Agentic RAG Workflow](https://sajalsharma.com/posts/comprehensive-agentic-rag/)
- [LangGraph Documentation](https://github.com/langchain-ai/langgraph)
- [Agentic RAG Survey (arXiv)](https://arxiv.org/abs/2501.09136)
