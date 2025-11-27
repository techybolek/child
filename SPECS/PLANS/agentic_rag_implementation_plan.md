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

## Phase 3 Implementation Plan

### Purpose
Replace the simple 2-way intent classifier with an intelligent 5-way router that selects the optimal processing path.

### Router Categories

| Route | Description | When to Use |
|-------|-------------|-------------|
| `rag` | Full RAG pipeline | Policy questions, eligibility, procedures |
| `location` | Facility search | "Find childcare near..." |
| `conversational` | Direct LLM response | Greetings, clarifications, meta-questions |
| `out_of_scope` | Polite decline | Non-childcare topics |
| `clarify` | Request more info | Ambiguous queries (feeds Phase 5) |

### Step 1: Extend RAGState
```python
# Add to chatbot/graph/state.py
route: Literal["rag", "location", "conversational", "out_of_scope", "clarify"] | None
routing_confidence: float | None  # 0.0-1.0
```

### Step 2: Create Router Node
```python
# chatbot/graph/nodes/router.py
from pydantic import BaseModel, Field

class RouterDecision(BaseModel):
    route: Literal["rag", "location", "conversational", "out_of_scope", "clarify"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str

ROUTER_PROMPT = """You are a router for a Texas childcare assistance chatbot.

Classify the user query into one of these categories:
- rag: Questions about childcare policies, eligibility, income limits, subsidies, procedures
- location: Requests to find childcare facilities or providers
- conversational: Greetings, thanks, meta-questions about the bot itself
- out_of_scope: Topics unrelated to Texas childcare (weather, sports, general knowledge)
- clarify: Query is too vague to process (e.g., "help me", "what can you do")

Conversation context:
{conversation_history}

Current query: {query}

Return JSON with: route, confidence (0-1), reasoning
"""

def router_node(state: RAGState) -> dict:
    llm = get_llm().with_structured_output(RouterDecision)
    decision = llm.invoke(ROUTER_PROMPT.format(
        conversation_history=format_messages(state.get("messages", [])),
        query=state["rewritten_query"] or state["query"]
    ))
    return {
        "route": decision.route,
        "routing_confidence": decision.confidence
    }
```

### Step 3: Create New Handler Nodes
```python
# chatbot/graph/nodes/conversational.py
def conversational_node(state: RAGState) -> dict:
    """Handle greetings, thanks, meta-questions without RAG."""
    response = llm.invoke(
        "You are a helpful Texas childcare assistant. "
        "Respond briefly to: {query}".format(query=state["query"])
    )
    return {
        "answer": response.content,
        "response_type": "conversational",
        "sources": []
    }

# chatbot/graph/nodes/out_of_scope.py
def out_of_scope_node(state: RAGState) -> dict:
    """Politely decline out-of-scope questions."""
    return {
        "answer": "I specialize in Texas childcare assistance programs. "
                  "I can help with eligibility, income limits, subsidies, "
                  "and finding childcare providers. How can I assist you with childcare?",
        "response_type": "out_of_scope",
        "sources": []
    }
```

### Step 4: Update Graph
```python
# In chatbot/graph/builder.py
workflow.add_node("router", router_node)
workflow.add_node("conversational", conversational_node)
workflow.add_node("out_of_scope", out_of_scope_node)

# Replace classify with router after rewrite
workflow.add_edge("rewrite", "router")

workflow.add_conditional_edges(
    "router",
    route_by_decision,
    {
        "rag": "retrieve",
        "location": "location",
        "conversational": "conversational",
        "out_of_scope": "out_of_scope",
        "clarify": "clarify"  # Phase 5
    }
)
```

### Step 5: Test Router
```bash
pytest tests/test_router.py -v
```
Test cases:
- "What are the income limits?" → `rag`
- "Find childcare in Austin" → `location`
- "Hello!" → `conversational`
- "What's the weather?" → `out_of_scope`
- "Help" → `clarify`

---

## Phase 4 Implementation Plan

### Purpose
Add a validation layer between generation and response that checks:
1. Answer is grounded in retrieved chunks (no hallucination)
2. Answer actually addresses the question
3. Confidence meets threshold

### Step 1: Extend RAGState
```python
# Add to chatbot/graph/state.py
draft_answer: str | None           # Before validation
validation_passed: bool | None
validation_issues: list[str]
validation_retry_count: int
```

### Step 2: Create Validator Node
```python
# chatbot/graph/nodes/validate.py
from pydantic import BaseModel

class ValidationResult(BaseModel):
    is_grounded: bool
    addresses_question: bool
    issues: list[str]
    confidence: float

VALIDATOR_PROMPT = """You are a strict fact-checker for a childcare assistance chatbot.

Retrieved source chunks:
{chunks}

User question: {query}

Draft answer: {draft_answer}

Evaluate:
1. is_grounded: Does EVERY claim in the answer appear in the source chunks?
2. addresses_question: Does the answer actually answer what was asked?
3. issues: List any problems found (empty if none)
4. confidence: 0-1 score of answer quality

Be strict. If the answer includes ANY information not in the sources, mark is_grounded=false.
"""

VALIDATION_THRESHOLD = 0.7
MAX_VALIDATION_RETRIES = 2

def validate_node(state: RAGState) -> dict:
    llm = get_llm().with_structured_output(ValidationResult)
    result = llm.invoke(VALIDATOR_PROMPT.format(
        chunks=format_chunks(state["reranked_chunks"]),
        query=state["query"],
        draft_answer=state["draft_answer"]
    ))
    passed = (
        result.is_grounded and
        result.addresses_question and
        result.confidence >= VALIDATION_THRESHOLD
    )
    return {
        "validation_passed": passed,
        "validation_issues": result.issues,
    }
```

### Step 3: Create Retry and Fallback Nodes
```python
# chatbot/graph/edges.py
def route_after_validation(state: RAGState) -> str:
    if state["validation_passed"]:
        return "finalize"
    if state["validation_retry_count"] >= MAX_VALIDATION_RETRIES:
        return "fallback"
    return "regenerate"

# chatbot/graph/nodes/regenerate.py
def regenerate_node(state: RAGState) -> dict:
    """Regenerate with explicit grounding instruction."""
    issues = state.get("validation_issues", [])
    stricter_prompt = GENERATE_PROMPT + f"""

IMPORTANT: Your previous answer had these issues: {issues}
Only use information from the provided chunks. Do not add any external knowledge.
"""
    # ... regenerate ...
    return {
        "draft_answer": new_answer,
        "validation_retry_count": state["validation_retry_count"] + 1
    }

# chatbot/graph/nodes/fallback.py
def fallback_node(state: RAGState) -> dict:
    """Provide best-effort response with uncertainty caveat."""
    return {
        "answer": f"Based on the available information: {state['draft_answer']}\n\n"
                  "Note: I wasn't able to fully verify this answer against my sources. "
                  "Please verify with TWC directly for critical decisions.",
        "response_type": "fallback",
        "sources": state.get("sources", [])
    }
```

### Step 4: Update Graph with Validation Loop
```python
# In chatbot/graph/builder.py

# Split generate into draft → validate → finalize
workflow.add_node("generate_draft", generate_draft_node)
workflow.add_node("validate", validate_node)
workflow.add_node("regenerate", regenerate_node)
workflow.add_node("finalize", finalize_node)
workflow.add_node("fallback", fallback_node)

workflow.add_edge("rerank", "generate_draft")
workflow.add_edge("generate_draft", "validate")

workflow.add_conditional_edges(
    "validate",
    route_after_validation,
    {
        "finalize": "finalize",
        "regenerate": "regenerate",
        "fallback": "fallback"
    }
)

workflow.add_edge("regenerate", "validate")  # Loop back
workflow.add_edge("finalize", END)
workflow.add_edge("fallback", END)
```

### Step 5: Test Validator
```bash
pytest tests/test_validator.py -v
```
Test cases:
- Grounded answer → passes
- Answer with hallucinated fact → fails, retries
- Completely off-topic answer → fails, goes to fallback
- Answer after 2 retries still failing → fallback with caveat

---

## Phase 5 Implementation Plan

### Purpose
When the router detects an ambiguous query, pause execution and ask the user for clarification before proceeding.

### Step 1: Extend RAGState
```python
# Add to chatbot/graph/state.py
clarification_needed: bool
clarification_question: str | None
clarification_options: list[str]
user_clarification: str | None  # Populated on resume
```

### Step 2: Create Clarification Node
```python
# chatbot/graph/nodes/clarify.py
from langgraph.types import interrupt
from pydantic import BaseModel

class ClarificationRequest(BaseModel):
    question: str
    options: list[str]  # 2-4 suggested options

CLARIFICATION_PROMPT = """The user query is ambiguous: "{query}"

Generate a clarifying question with 2-4 options.
Example:
- Query: "What are the requirements?"
- Question: "Which requirements would you like to know about?"
- Options: ["Income eligibility", "Provider licensing", "Application process"]
"""

def clarify_node(state: RAGState) -> dict:
    llm = get_llm().with_structured_output(ClarificationRequest)
    request = llm.invoke(CLARIFICATION_PROMPT.format(query=state["query"]))

    # LangGraph interrupt - pauses graph execution
    user_response = interrupt({
        "type": "clarification_needed",
        "question": request.question,
        "options": request.options
    })

    # Execution resumes here after user responds
    return {
        "user_clarification": user_response,
        "query": f"{state['query']} - specifically: {user_response}"
    }
```

### Step 3: Define API Contract
```python
# backend/api/models.py
from pydantic import BaseModel
from typing import Literal

class ChatResponse(BaseModel):
    response_type: Literal["answer", "clarification_needed", "error"]
    answer: str | None = None
    sources: list[dict] | None = None
    clarification_question: str | None = None
    clarification_options: list[str] | None = None
    thread_id: str

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    clarification_response: str | None = None
```

### Step 4: Update Backend to Handle Interrupts
```python
# backend/api/routes.py
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        config = {"configurable": {"thread_id": request.thread_id or str(uuid4())}}

        if request.clarification_response:
            result = chatbot.graph.invoke(
                Command(resume=request.clarification_response),
                config
            )
        else:
            result = chatbot.graph.invoke({"query": request.message}, config)

        return ChatResponse(
            response_type="answer",
            answer=result["answer"],
            sources=result["sources"],
            thread_id=config["configurable"]["thread_id"]
        )
    except GraphInterrupt as e:
        interrupt_data = e.value
        return ChatResponse(
            response_type="clarification_needed",
            clarification_question=interrupt_data["question"],
            clarification_options=interrupt_data["options"],
            thread_id=config["configurable"]["thread_id"]
        )
```

### Step 5: Update Frontend
```typescript
// frontend/components/ChatInterface.tsx
interface ClarificationUI {
  question: string;
  options: string[];
  threadId: string;
}

const [clarification, setClarification] = useState<ClarificationUI | null>(null);

const handleResponse = (response: ChatResponse) => {
  if (response.response_type === "clarification_needed") {
    setClarification({
      question: response.clarification_question!,
      options: response.clarification_options!,
      threadId: response.thread_id
    });
  } else {
    addMessage({ role: "assistant", content: response.answer });
    setClarification(null);
  }
};

// Render clarification UI
{clarification && (
  <div className="clarification-panel">
    <p>{clarification.question}</p>
    {clarification.options.map(option => (
      <button key={option} onClick={() => sendClarification(option, clarification.threadId)}>
        {option}
      </button>
    ))}
    <input placeholder="Or type your own..." onSubmit={...} />
  </div>
)}
```

### Step 6: Update Graph
```python
# In chatbot/graph/builder.py
workflow.add_node("clarify", clarify_node)
workflow.add_edge("clarify", "router")  # Loop back with enriched query

# IMPORTANT: Checkpointer required for interrupts
def build_rag_graph(checkpointer=None):
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["clarify"]
    )
```

### Step 7: Test Clarification
```bash
pytest tests/test_clarification.py -v
```
Test cases:
- Ambiguous query → interrupt triggered, options returned
- User selects option → graph resumes, processes enriched query
- User types custom response → graph resumes with custom text
- Non-ambiguous query → no interrupt, normal flow

---

## Error Handling

### Node-Level Error Boundaries
```python
# chatbot/graph/utils/error_handler.py
from functools import wraps

class RAGError(Exception):
    def __init__(self, message: str, recoverable: bool = True):
        self.message = message
        self.recoverable = recoverable

def with_error_handling(fallback_state: dict):
    def decorator(func):
        @wraps(func)
        def wrapper(state):
            try:
                return func(state)
            except Exception as e:
                logger.error(f"Node {func.__name__} failed: {e}")
                if isinstance(e, RAGError) and e.recoverable:
                    return fallback_state
                raise
        return wrapper
    return decorator

# Usage
@with_error_handling(fallback_state={"retrieved_chunks": []})
def retrieve_node(state: RAGState) -> dict:
    ...
```

### Graceful Degradation Paths
| Error | Degradation |
|-------|-------------|
| Retrieval fails | Return empty chunks → generate "I couldn't find information" |
| Router LLM fails | Default to `rag` route |
| Validator LLM fails | Skip validation, pass draft through |
| Clarification interrupt fails | Proceed with original query |

### Rate Limiting
```python
# chatbot/config.py
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF = [1, 2, 4]  # seconds

@retry(
    stop=stop_after_attempt(RATE_LIMIT_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RateLimitError)
)
def call_llm(prompt):
    return llm.invoke(prompt)
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
| 3 | `chatbot/graph/state.py` | Add `route`, `routing_confidence` fields |
| 3 | `chatbot/graph/nodes/router.py` | Create router node |
| 3 | `chatbot/graph/nodes/conversational.py` | Create conversational node |
| 3 | `chatbot/graph/nodes/out_of_scope.py` | Create out_of_scope node |
| 3 | `chatbot/graph/builder.py` | Add router, new nodes, update edges |
| 3 | `chatbot/graph/edges.py` | Add `route_by_decision` function |
| 4 | `chatbot/graph/state.py` | Add `draft_answer`, `validation_*` fields |
| 4 | `chatbot/graph/nodes/validate.py` | Create validator node |
| 4 | `chatbot/graph/nodes/regenerate.py` | Create regenerate node |
| 4 | `chatbot/graph/nodes/fallback.py` | Create fallback node |
| 4 | `chatbot/graph/nodes/generate.py` | Rename to `generate_draft`, output to `draft_answer` |
| 4 | `chatbot/graph/builder.py` | Add validation loop |
| 4 | `chatbot/graph/edges.py` | Add `route_after_validation` |
| 5 | `chatbot/graph/state.py` | Add clarification fields |
| 5 | `chatbot/graph/nodes/clarify.py` | Create clarify node with interrupt |
| 5 | `chatbot/graph/builder.py` | Add clarify node, configure interrupt |
| 5 | `backend/api/routes.py` | Handle GraphInterrupt, update request/response models |
| 5 | `backend/api/models.py` | Create ChatRequest/ChatResponse models |
| 5 | `frontend/components/ChatInterface.tsx` | Add clarification UI |
| - | `chatbot/graph/utils/error_handler.py` | Create error handling decorator |
