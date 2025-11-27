# Agentic RAG Implementation Plan

**Date:** 2025-11-27
**Status:** Ready for implementation

---

## Executive Summary

This document defines the implementation plan for adding conversational capabilities to the Texas Childcare Chatbot. The current system is 100% stateless - each question is processed in isolation with no memory of previous interactions.

The plan adds 5 phases of agentic features, starting with low-risk conversation memory and progressing to more complex routing and human-in-the-loop clarification.

---

## Implementation Phases

| Phase | Component | Risk | Description |
|-------|-----------|------|-------------|
| 1 | Conversation memory (checkpointer) | Low | Enables multi-turn conversations |
| 2 | Query rewriter | Low | Expands ambiguous follow-up questions |
| 3 | Router (5-way decision) | Medium | Intelligent path selection |
| 4 | Validator | Medium | Checks groundedness, prevents hallucinations |
| 5 | Clarification (human-in-the-loop) | High | Asks user for more info when needed |

---

## Design Decisions

### Key Principles

1. **Phased approach** - Low-risk phases first (1→2), high-risk last (5)
2. **Single codebase** - LangGraph for both stateless and conversational modes
3. **Feature flags** - `CONVERSATIONAL_MODE` controls behavior
4. **Backward compatible** - Existing API works unchanged when flag is off
5. **Minimal state changes** - Only add state fields when needed by each phase

### Issues & Recommendations

#### 1. State Explosion in AgentState

**Issue**: The full `AgentState` (for Phase 3+) has 12+ fields. Some fields have overlapping purposes:
- `original_query` vs first entry in `messages`
- `draft_answer` vs `final_answer` (redundant if validator passes)

**Recommendation**: For Phase 1, extend current `RAGState` minimally:
```python
class RAGState(TypedDict):
    # Existing fields...
    messages: list[BaseMessage]  # Add for conversation history
    thread_id: str | None        # Add for checkpointer
```

Don't add `draft_answer`, `confidence`, etc. until Phases 4-5 actually need them.

#### 2. Query Rewriter Prompt Complexity

**Issue**: The rewriter examples show significant context expansion:
- "What about family of 5?" → "What is the income eligibility limit for a family of 5 in BCY 2026?"

This requires the LLM to infer "BCY 2026" from conversation context that may be several turns back.

**Recommendation**: Include the previous answer snippet in the rewriter prompt, not just the conversation structure. The rewriter needs access to the actual retrieved content, not just Q&A pairs.

#### 3. Clarification Node Human-in-the-Loop

**Issue**: Phase 5's `interrupt()` mechanism requires careful frontend integration:
```python
user_response = interrupt({
    "type": "clarification_needed",
    "question": question.clarifying_question,
    "options": question.suggested_options
})
```

The current frontend (`frontend/`) doesn't support interrupt handling. It expects a single response per request.

**Recommendation**: Before Phase 5:
1. Design the API contract for interrupts (e.g., `response_type: "clarification_needed"`)
2. Update `backend/api/routes.py` to handle interrupted states
3. Update frontend to render clarification UI and submit responses

#### 4. Missing Error Handling Design

**Issue**: The design shows happy-path flows but doesn't address:
- What happens if retrieval returns 0 chunks?
- What if the router LLM call fails?
- Rate limiting on GROQ/OpenAI?
- Timeout handling for long chains?

**Recommendation**: Add an "Error Handling" section to the design doc covering:
- Node-level error boundaries
- Graceful degradation paths
- User-facing error messages

#### 5. Retry Logic Bounds

**Issue**: The design uses `retry_count < 2` in multiple places but doesn't specify:
- Is this per-turn or per-session?
- Does it reset between different retry types?
- What happens at max retries?

**Recommendation**: Define explicit retry semantics:
```python
class AgentState(TypedDict):
    # ...
    rewrite_retry_count: int   # Separate counters
    validation_retry_count: int
```

#### 6. CONVERSATIONAL_MODE Flag Not Wired

**Issue**: The `CONVERSATIONAL_MODE` flag exists in `chatbot/config.py:86` but is **never checked** in the current code.

**Recommendation**: Wire up the flag in Phase 1:
```python
# In chatbot/graph/builder.py
def get_graph():
    if config.CONVERSATIONAL_MODE:
        checkpointer = InMemorySaver()
        return build_graph(checkpointer=checkpointer)
    return build_graph()  # Stateless
```

---

## Phase 1 Implementation Plan

### Step 1: Extend RAGState (minimal)
```python
# Add to chatbot/graph/state.py
messages: Annotated[list[BaseMessage], add_messages]  # LangGraph reducer
thread_id: str | None
```

### Step 2: Add Checkpointer (InMemorySaver for dev)
```python
# In chatbot/graph/builder.py
from langgraph.checkpoint.memory import InMemorySaver

def build_graph(checkpointer=None):
    # ... existing code ...
    return workflow.compile(checkpointer=checkpointer)

def get_graph():
    if config.CONVERSATIONAL_MODE:
        checkpointer = InMemorySaver()
        return build_graph(checkpointer=checkpointer)
    return build_graph()
```

### Step 3: Update Chatbot Invocation
```python
# In chatbot/chatbot.py
def ask(self, question: str, thread_id: str = None, debug: bool = False):
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}

    final_state = self.graph.invoke(initial_state, config)
```

### Step 4: Update Backend API
```python
# In backend/api/routes.py
class ChatRequest(BaseModel):
    message: str
    thread_id: str = None  # New field
```

### Step 5: Test Conversation Memory
- Create multi-turn test cases in `QUESTIONS/conversational/`
- Verify same `thread_id` maintains history
- Verify different `thread_id` starts fresh

---

## Phase 2 Implementation Plan

### Step 1: Create Rewriter Prompt
```python
# chatbot/prompts/agentic/query_rewriter_prompt.py
QUERY_REWRITER_PROMPT = """Given the conversation history and a follow-up question,
rewrite the question to be self-contained.

Conversation:
{conversation}

Previous answer snippet:
{previous_answer_snippet}

Follow-up question: {query}

Rewritten question:"""
```

### Step 2: Create Rewriter Node
```python
# chatbot/graph/nodes/rewrite.py
def rewrite_node(state: RAGState) -> dict:
    if not needs_rewriting(state["query"], state["messages"]):
        return {"rewritten_query": None}

    rewritten = llm.invoke(QUERY_REWRITER_PROMPT.format(...))
    return {"rewritten_query": rewritten}
```

### Step 3: Update Graph with Conditional Rewriting
```python
# Add rewrite node before retrieve
workflow.add_node("rewrite", rewrite_node)
workflow.add_edge("classify", "rewrite")
workflow.add_conditional_edges("rewrite", route_after_rewrite)
```

### Step 4: Update Retrieve Node
```python
# Use rewritten query if available
query = state["rewritten_query"] or state["query"]
```

---

## Testing Requirements

> **IMPORTANT:** All tests must be EXECUTED, not just created. Each phase is not complete until all tests pass.

### Existing Tests

The project has an existing e2e test that validates the evaluation framework:

```bash
# Run existing e2e test - MUST PASS before starting Phase 1
pytest tests/test_evaluation_e2e.py -v

# Or direct execution
python tests/test_evaluation_e2e.py
```

This test validates: evaluation completion, artifact creation, result format, summary statistics, and pass rate.

### Before Phase 1

1. **Run existing e2e test** to confirm baseline works:
   ```bash
   pytest tests/test_evaluation_e2e.py -v  # MUST PASS
   ```

2. **Run existing evaluation** to establish baseline metrics:
   ```bash
   python -m evaluation.run_evaluation --mode hybrid
   ```

3. **Create conversational test cases** at `QUESTIONS/conversational/`:
   ```markdown
   # income-followup.md
   ## Turn 1
   User: What's the income limit for a family of 4?
   Expected: $92,041...

   ## Turn 2
   User: What about family of 5?
   Expected: $106,768...
   ```

### During Implementation

4. **Create AND RUN unit tests for checkpointer behavior**:
   ```bash
   # Create tests/test_checkpointer.py, then execute:
   pytest tests/test_checkpointer.py -v  # MUST PASS
   ```
   Test cases:
   - Same thread_id → messages accumulate
   - Different thread_id → fresh state
   - No thread_id → stateless (legacy behavior)

5. **Create AND RUN unit tests for query rewriter** (Phase 2):
   ```bash
   # Create tests/test_query_rewriter.py, then execute:
   pytest tests/test_query_rewriter.py -v  # MUST PASS
   ```
   Test cases:
   - Ambiguous queries get rewritten
   - Clear queries pass through unchanged

### After Each Phase

6. **Run regression tests** - existing tests must still pass:
   ```bash
   pytest tests/test_evaluation_e2e.py -v  # MUST PASS
   ```

7. **Run evaluation suite** and compare to baseline:
   ```bash
   python -m evaluation.run_evaluation --mode hybrid
   # Compare scores to pre-Phase baseline
   ```

### Phase Completion Checklist

A phase is **NOT complete** until:
- [ ] All new unit tests created and passing
- [ ] Existing e2e test passing (`pytest tests/test_evaluation_e2e.py -v`)
- [ ] Evaluation scores not regressed from baseline

---

## Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|------------|
| 1 - Checkpointer | Low | Feature flag, backward compatible |
| 2 - Query Rewriter | Low | Can be disabled if results are poor |
| 3 - Router | Medium | Requires new prompt tuning, may route incorrectly |
| 4 - Validator | Medium | May reject good answers, needs calibration |
| 5 - Clarification | High | Requires frontend changes, UX complexity |

---

## Summary & Recommendations

1. **Implement Phases 1+2 together** - Low risk, high synergy (conversation memory + query rewriter)
2. **Establish baseline metrics** before starting
3. **Wire up CONVERSATIONAL_MODE flag** in Phase 1
4. **Defer Phases 3-5** until 1+2 results are evaluated
5. **Add error handling section** before Phase 3
6. **Plan frontend changes early** if Phase 5 (clarification) is desired

### Files to Modify

| Phase | File | Change |
|-------|------|--------|
| 1 | `chatbot/graph/state.py` | Add `messages`, `thread_id` fields |
| 1 | `chatbot/graph/builder.py` | Add checkpointer support, wire CONVERSATIONAL_MODE |
| 1 | `chatbot/chatbot.py` | Add `thread_id` parameter to `ask()` |
| 1 | `backend/api/routes.py` | Add `thread_id` to ChatRequest |
| 2 | `chatbot/prompts/agentic/query_rewriter_prompt.py` | Create new prompt |
| 2 | `chatbot/graph/nodes/rewrite.py` | Create rewriter node |
| 2 | `chatbot/graph/builder.py` | Add rewrite node to graph |
| 2 | `chatbot/graph/nodes/retrieve.py` | Use rewritten query if available |
