# Conversational RAG Design

Transform the stateless RAG pipeline into a multi-turn conversational system with automatic testing.

## Current State Analysis

**Existing Architecture:**
```
Query → Classify → Retrieve → Rerank → Generate → Response (stateless)
```

**Key Files:**
- `chatbot/graph/state.py` - `RAGState` (no memory)
- `chatbot/graph/builder.py` - Compiles without checkpointer
- `chatbot/chatbot.py` - `TexasChildcareChatbot.ask()` single-turn

**Gap:** No conversation history, no query reformulation, no context accumulation.

---

## Phase 1: Conversational State & Memory

### 1.1 Extended State Definition

```python
# chatbot/graph/state.py
from typing import TypedDict, Literal, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ConversationalRAGState(TypedDict):
    """State for conversational RAG pipeline."""
    
    # Conversation history (accumulated via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Current turn
    query: str                              # Original user query
    reformulated_query: str | None          # History-aware query for retrieval
    
    # Routing
    intent: Literal["information", "location_search", "clarification", "followup"] | None
    needs_clarification: bool
    
    # Retrieval
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    
    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]
    
    # Debug
    debug: bool
    debug_info: dict | None
```

### 1.2 Memory Architecture

```python
# chatbot/memory.py
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver  # Production

class MemoryManager:
    """Thread-scoped conversation memory."""
    
    def __init__(self, backend: str = "memory"):
        if backend == "memory":
            self.checkpointer = InMemorySaver()
        elif backend == "postgres":
            self.checkpointer = PostgresSaver.from_conn_string(
                os.getenv("POSTGRES_URI")
            )
    
    def get_thread_config(self, thread_id: str) -> dict:
        """Get config for a conversation thread."""
        return {"configurable": {"thread_id": thread_id}}
```

---

## Phase 2: Query Reformulation Node

### 2.1 History-Aware Query Rewriting

The most critical component for conversational RAG. Transforms context-dependent queries into standalone queries.

> **Prompt:** See [conversational_prompts_design.md](./conversational_prompts_design.md#prompt-1-query-reformulation)

```python
# chatbot/graph/nodes/reformulate.py
from chatbot.prompts.conversational.reformulation_prompt import (
    REFORMULATION_SYSTEM, REFORMULATION_USER
)

def reformulate_node(state: ConversationalRAGState) -> dict:
    """Reformulate query using conversation history."""
    
    messages = state.get("messages", [])
    
    # If no history, use original query
    if len(messages) <= 1:
        return {"reformulated_query": state["query"]}
    
    # Format history for prompt
    history = format_conversation_history(messages[:-1])
    
    response = llm.invoke([
        SystemMessage(content=REFORMULATION_SYSTEM),
        HumanMessage(content=REFORMULATION_USER.format(
            history=history, query=state["query"]
        ))
    ])
    
    reformulated = extract_tag(response.content, "reformulated_query")
    
    return {"reformulated_query": reformulated or state["query"]}
```

---

## Phase 3: Enhanced Graph Architecture

### 3.1 Conversational Graph Builder

```python
# chatbot/graph/builder.py
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver

from .state import ConversationalRAGState
from .nodes.reformulate import reformulate_node
from .nodes.classify import classify_node
from .nodes.retrieve import retrieve_node
from .nodes.rerank import rerank_node
from .nodes.generate import generate_node
from .nodes.location import location_node
from .edges import route_by_intent, should_clarify


def build_conversational_graph(checkpointer=None):
    """Build conversational RAG graph with memory.
    
    Graph structure:
        START → REFORMULATE → CLASSIFY → [conditional]
                                           ├── RETRIEVE → RERANK → GENERATE → END
                                           ├── LOCATION → END
                                           └── CLARIFY → END
    """
    workflow = StateGraph(ConversationalRAGState)
    
    # Add nodes
    workflow.add_node("reformulate", reformulate_node)  # NEW
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)
    workflow.add_node("clarify", clarify_node)  # NEW
    
    # Entry: reformulate first
    workflow.add_edge(START, "reformulate")
    workflow.add_edge("reformulate", "classify")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "location": "location",
            "clarify": "clarify"
        }
    )
    
    # RAG path
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)
    
    # Other paths
    workflow.add_edge("location", END)
    workflow.add_edge("clarify", END)
    
    # Compile with checkpointer for memory
    if checkpointer is None:
        checkpointer = InMemorySaver()
    
    print("[Graph Builder] Building conversational RAG graph with memory")
    return workflow.compile(checkpointer=checkpointer)
```

### 3.2 Updated Chatbot Interface

```python
# chatbot/chatbot.py
import uuid
from .graph.builder import build_conversational_graph
from .memory import MemoryManager

class TexasChildcareChatbot:
    """Conversational RAG chatbot with multi-turn memory."""
    
    def __init__(self, memory_backend: str = "memory"):
        self.memory = MemoryManager(backend=memory_backend)
        self.graph = build_conversational_graph(
            checkpointer=self.memory.checkpointer
        )
    
    def ask(
        self, 
        question: str, 
        thread_id: str | None = None,
        debug: bool = False
    ) -> dict:
        """Ask a question with conversation context.
        
        Args:
            question: User's question
            thread_id: Conversation thread ID (auto-generated if None)
            debug: Enable debug output
        
        Returns:
            dict with answer, sources, thread_id, turn_count
        """
        # Generate thread ID for new conversations
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        config = self.memory.get_thread_config(thread_id)
        
        # Input as message (LangGraph accumulates via add_messages)
        input_state = {
            "messages": [HumanMessage(content=question)],
            "query": question,
            "debug": debug,
        }
        
        # Invoke with thread config
        final_state = self.graph.invoke(input_state, config)
        
        # Get conversation length from checkpoint
        turn_count = len(final_state.get("messages", [])) // 2
        
        return {
            "answer": final_state["answer"],
            "sources": final_state["sources"],
            "thread_id": thread_id,
            "turn_count": turn_count,
            "reformulated_query": final_state.get("reformulated_query"),
            "response_type": final_state["response_type"],
        }
    
    def new_conversation(self) -> str:
        """Start a new conversation thread."""
        return str(uuid.uuid4())
    
    def get_history(self, thread_id: str) -> list[dict]:
        """Get conversation history for a thread."""
        config = self.memory.get_thread_config(thread_id)
        state = self.graph.get_state(config)
        
        messages = state.values.get("messages", [])
        return [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant", 
             "content": m.content}
            for m in messages
        ]
```

---

## Phase 4: Retrieval Enhancements

### 4.1 Context-Aware Retrieval

Use `reformulated_query` instead of raw `query` for retrieval.

```python
# chatbot/graph/nodes/retrieve.py (updated)

def retrieve_node(state: ConversationalRAGState) -> dict:
    """Retrieve using reformulated query."""
    
    # Use reformulated query if available
    query = state.get("reformulated_query") or state["query"]
    
    chunks = hybrid_retriever.retrieve(query, top_k=config.RETRIEVAL_TOP_K)
    
    return {"retrieved_chunks": chunks}
```

### 4.2 Conversation-Aware Reranking

Include conversation context in reranking prompt.

> **Prompt:** See [conversational_prompts_design.md](./conversational_prompts_design.md#prompt-3-reranking-conversation-aware)

```python
# chatbot/graph/nodes/rerank.py (updated)
from chatbot.prompts.conversational.reranking_prompt import (
    RERANKING_PROMPT, RERANKING_PROMPT_CONVERSATIONAL, format_chunks_xml
)

def rerank_node(state: ConversationalRAGState) -> dict:
    """Rerank with optional conversation context."""
    
    messages = state.get("messages", [])
    has_history = len(messages) > 1
    
    prompt = RERANKING_PROMPT_CONVERSATIONAL if has_history else RERANKING_PROMPT
    # ... scoring logic
```

---

## Phase 5: Automatic Testing Framework

### 5.1 Multi-Turn Test Format

```yaml
# QUESTIONS/conversations/ccs_eligibility_conv.yaml
name: "CCS Eligibility Multi-Turn"
description: "Tests income eligibility flow with follow-ups"
domain: "eligibility"

conversation:
  - turn: 1
    user: "What are the income limits for childcare assistance in Texas?"
    expected_topics: ["SMI", "income eligibility", "percentage"]
    min_score: 70
    
  - turn: 2
    user: "What about for a family of 4?"
    requires_context: true  # Must resolve "What about" from turn 1
    expected_answer_contains: ["family of 4", "income", "$"]
    min_score: 70
    
  - turn: 3
    user: "And if they make $5,000 per month?"
    requires_context: true  # Must resolve "they" and remember family size
    expected_intent: "eligibility_check"
    min_score: 70
    
  - turn: 4
    user: "How do I apply?"
    requires_context: true  # Should know we're talking about CCS
    expected_answer_contains: ["apply", "CCS", "local workforce"]
    min_score: 70

success_criteria:
  min_average_score: 75
  all_turns_pass: true
  context_resolution_rate: 1.0  # All context-dependent turns resolved correctly
```

### 5.2 Conversation Evaluator

```python
# evaluation/conversation_evaluator.py
from dataclasses import dataclass
from typing import Literal
import yaml

@dataclass
class TurnResult:
    turn_number: int
    user_query: str
    reformulated_query: str | None
    response: str
    expected_topics: list[str]
    
    # Scores
    factual_accuracy: float
    completeness: float
    context_resolution: float  # Did it correctly resolve references?
    coherence: float
    composite_score: float
    
    passed: bool
    
@dataclass  
class ConversationResult:
    name: str
    thread_id: str
    turns: list[TurnResult]
    
    # Aggregate metrics
    average_score: float
    context_resolution_rate: float
    all_turns_passed: bool
    conversation_passed: bool


class ConversationEvaluator:
    """Evaluates multi-turn conversations."""
    
    def __init__(self, chatbot: TexasChildcareChatbot, judge: LLMJudge):
        self.chatbot = chatbot
        self.judge = judge
    
    def evaluate_conversation(self, conv_file: str) -> ConversationResult:
        """Run and evaluate a full conversation."""
        
        conv_spec = yaml.safe_load(open(conv_file))
        
        # Start new conversation
        thread_id = self.chatbot.new_conversation()
        turn_results = []
        
        for turn_spec in conv_spec["conversation"]:
            result = self._evaluate_turn(
                thread_id=thread_id,
                turn_spec=turn_spec,
                previous_turns=turn_results
            )
            turn_results.append(result)
            
            # Stop on fail (optional)
            if not result.passed and conv_spec.get("stop_on_fail", True):
                break
        
        return self._aggregate_results(conv_spec["name"], thread_id, turn_results)
    
    def _evaluate_turn(
        self, 
        thread_id: str, 
        turn_spec: dict,
        previous_turns: list[TurnResult]
    ) -> TurnResult:
        """Evaluate a single turn in context."""
        
        # Get chatbot response
        response = self.chatbot.ask(
            question=turn_spec["user"],
            thread_id=thread_id,
            debug=True
        )
        
        # Score with judge
        scores = self.judge.score_turn(
            query=turn_spec["user"],
            reformulated_query=response.get("reformulated_query"),
            response=response["answer"],
            expected_topics=turn_spec.get("expected_topics", []),
            expected_answer_contains=turn_spec.get("expected_answer_contains", []),
            requires_context=turn_spec.get("requires_context", False),
            previous_turns=previous_turns
        )
        
        # Context resolution check
        context_score = self._check_context_resolution(
            turn_spec, response, previous_turns
        ) if turn_spec.get("requires_context") else 1.0
        
        composite = self._calculate_composite(scores, context_score)
        
        return TurnResult(
            turn_number=turn_spec["turn"],
            user_query=turn_spec["user"],
            reformulated_query=response.get("reformulated_query"),
            response=response["answer"],
            expected_topics=turn_spec.get("expected_topics", []),
            factual_accuracy=scores["accuracy"],
            completeness=scores["completeness"],
            context_resolution=context_score,
            coherence=scores["coherence"],
            composite_score=composite,
            passed=composite >= turn_spec.get("min_score", 70)
        )
    
    def _check_context_resolution(
        self,
        turn_spec: dict,
        response: dict,
        previous_turns: list[TurnResult]
    ) -> float:
        """Check if context-dependent references were resolved."""
        
        reformulated = response.get("reformulated_query", "")
        
        # Check if pronouns/references were expanded
        context_markers = ["it", "they", "this", "that", "what about", "how about"]
        original_has_markers = any(m in turn_spec["user"].lower() for m in context_markers)
        
        if not original_has_markers:
            return 1.0  # No context needed
        
        # Reformulated should be longer and more specific
        if len(reformulated) <= len(turn_spec["user"]):
            return 0.0  # Failed to expand
        
        # Check for expected entity resolution
        if previous_turns:
            last_response = previous_turns[-1].response
            # Simple heuristic: reformulated should include key terms from context
            key_terms = self._extract_key_terms(last_response)
            resolved = sum(1 for t in key_terms if t.lower() in reformulated.lower())
            return min(1.0, resolved / max(1, len(key_terms)))
        
        return 0.5  # Partial credit
```

### 5.3 Multi-Turn Judge

> **Prompt:** See [conversational_prompts_design.md](./conversational_prompts_design.md#prompt-5-multi-turn-judge)

```python
# evaluation/multi_turn_judge.py
from evaluation.prompts.multi_turn_judge_prompt import MULTI_TURN_JUDGE_PROMPT

class MultiTurnJudge:
    """LLM-as-a-Judge for multi-turn conversations."""
    
    def score_turn(
        self,
        query: str,
        reformulated_query: str | None,
        response: str,
        expected_topics: list[str],
        expected_answer_contains: list[str],
        requires_context: bool,
        previous_turns: list[TurnResult]
    ) -> dict:
        """Score a single turn with conversation context."""
        
        history = self._format_history(previous_turns)
        
        prompt = MULTI_TURN_JUDGE_PROMPT.format(
            conversation_history=history,
            original_query=query,
            reformulated_query=reformulated_query or query,
            response=response,
            expected_topics=", ".join(expected_topics),
            expected_contains=", ".join(expected_answer_contains),
            requires_context=requires_context
        )
        
        result = self.llm.invoke(prompt)
        return json.loads(result.content)
```

### 5.4 Test Runner

```python
# evaluation/run_conversation_eval.py
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["hybrid", "dense"], default="hybrid")
    parser.add_argument("--conversation", help="Single conversation file")
    parser.add_argument("--all", action="store_true", help="Run all conversations")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    # Initialize
    chatbot = TexasChildcareChatbot()
    judge = MultiTurnJudge()
    evaluator = ConversationEvaluator(chatbot, judge)
    
    # Find conversation files
    conv_dir = Path("QUESTIONS/conversations")
    if args.conversation:
        files = [conv_dir / args.conversation]
    else:
        files = list(conv_dir.glob("*.yaml"))
    
    # Run evaluations
    results = []
    for conv_file in files:
        print(f"\n{'='*60}")
        print(f"Evaluating: {conv_file.name}")
        print('='*60)
        
        result = evaluator.evaluate_conversation(str(conv_file))
        results.append(result)
        
        # Print turn-by-turn
        for turn in result.turns:
            status = "PASS" if turn.passed else "FAIL"
            print(f"  Turn {turn.turn_number}: {status} ({turn.composite_score:.1f})")
            if args.debug:
                print(f"    Original: {turn.user_query}")
                print(f"    Reformulated: {turn.reformulated_query}")
                print(f"    Context Resolution: {turn.context_resolution:.2f}")
        
        conv_status = "PASS" if result.conversation_passed else "FAIL"
        print(f"\n  Conversation: {conv_status}")
        print(f"  Average Score: {result.average_score:.1f}")
        print(f"  Context Resolution Rate: {result.context_resolution_rate:.1%}")
    
    # Summary
    print_summary(results)

if __name__ == "__main__":
    main()
```

---

## Phase 6: Evaluation Metrics

### 6.1 MTRAG-Inspired Metrics

Based on the [MTRAG benchmark](https://arxiv.org/abs/2501.03468), evaluate on:

| Metric | Description | Target |
|--------|-------------|--------|
| **FANC Score** | Faithfulness, Appropriateness, Naturalness, Completeness | >= 4.0/5.0 |
| **Later-Turn Performance** | Score degradation on turns 4+ | < 10% drop |
| **Context Resolution Rate** | Correct pronoun/reference resolution | >= 95% |
| **Non-Standalone Handling** | Correctly interprets context-dependent queries | >= 90% |

### 6.2 Ragas AspectCritic Integration

```python
# evaluation/aspect_critics.py
from ragas.metrics import AspectCritic

# Task completion - did the bot fully address the request?
task_completion = AspectCritic(
    name="task_completion",
    definition="""Return 1 if the AI assistant fully completed the user's request 
    without requiring re-asking or missing any part of the question. 
    Return 0 if the response was incomplete, off-topic, or required follow-up 
    clarification for the same information."""
)

# Context continuity - does it maintain conversation thread?
context_continuity = AspectCritic(
    name="context_continuity", 
    definition="""Return 1 if the AI correctly maintained context from previous 
    turns, correctly resolving pronouns and references. 
    Return 0 if it forgot context, asked for already-provided information, 
    or misinterpreted references."""
)

# Domain compliance - stays within Texas childcare assistance
domain_compliance = AspectCritic(
    name="domain_compliance",
    definition="""Return 1 if the AI stayed within the domain of Texas childcare 
    assistance programs (CCS, CCMS, eligibility, applications, providers).
    Return 0 if it provided information outside this domain or gave 
    financial/legal advice."""
)
```

---

## Phase 7: Test Scenarios

### 7.1 Core Conversation Patterns

| Pattern | Example Sequence | Tests |
|---------|-----------------|-------|
| **Pronoun Resolution** | "What is CCS?" → "How do I apply for it?" | `it` → CCS |
| **Implicit Context** | "Income limit for family of 3?" → "What about 4?" | Family size comparison |
| **Topic Continuation** | "Explain CCMS" → "What are the requirements?" | Maintains CCMS context |
| **Entity Tracking** | "I have 2 kids, make $3000" → "Am I eligible?" | Remembers user info |
| **Clarification Flow** | "Help with childcare" → (clarify) → "I need eligibility info" | Handles vague → specific |

### 7.2 Edge Cases

```yaml
# QUESTIONS/conversations/edge_cases.yaml
name: "Edge Cases"

conversation:
  # Topic switch mid-conversation
  - turn: 1
    user: "What is the income limit for CCS?"
    
  - turn: 2
    user: "Actually, where can I find a daycare near Austin?"
    expected_intent: "location_search"  # Should switch, not force CCS context
    
  # Correction handling
  - turn: 3
    user: "Sorry, I meant childcare assistance, not daycare locations"
    should_return_to: "eligibility"
    
  # Ambiguous reference
  - turn: 4
    user: "What are the requirements?"
    requires_disambiguation: true  # Multiple possible referents
```

---

## Phase 8: Implementation Roadmap

### Milestone 1: Basic Conversational Memory (1-2 days)
- [ ] Update `RAGState` → `ConversationalRAGState`
- [ ] Add `InMemorySaver` checkpointer to graph
- [ ] Update `TexasChildcareChatbot` with `thread_id` support
- [ ] Basic integration test

### Milestone 2: Query Reformulation (1-2 days)
- [ ] Implement `reformulate_node`
- [ ] Add to graph pipeline before `classify`
- [ ] Tune reformulation prompt for Texas childcare domain
- [ ] Unit tests for reformulation

### Milestone 3: Testing Framework (2-3 days)
- [ ] Define YAML conversation format
- [ ] Implement `ConversationEvaluator`
- [ ] Implement `MultiTurnJudge`
- [ ] Create 5-10 test conversations covering key patterns
- [ ] Integrate with existing evaluation runner

### Milestone 4: Advanced Features (optional)
- [ ] HyDE for complex queries
- [ ] Conversation-aware reranking
- [ ] Long-term memory store (cross-session)
- [ ] Clarification node for ambiguous queries

---

## Configuration Changes

```python
# chatbot/config.py (additions)

# ============================================================
# CONVERSATIONAL MODE - Master toggle
# ============================================================
# When False: Stateless RAG (current behavior)
#   - No memory, no reformulation, single-turn only
#   - Graph: classify → retrieve → rerank → generate
#
# When True: Conversational RAG (new behavior)
#   - Thread-scoped memory, query reformulation, multi-turn
#   - Graph: reformulate → classify → retrieve → rerank → generate
# ============================================================
CONVERSATIONAL_MODE = os.getenv("CONVERSATIONAL_MODE", "false").lower() == "true"

# Conversation settings (only used when CONVERSATIONAL_MODE=True)
MAX_CONVERSATION_TURNS = 20
MEMORY_BACKEND = "memory"  # or "postgres" for production
REFORMULATION_MODEL = "openai/gpt-oss-20b"
REFORMULATION_MAX_HISTORY_TURNS = 5  # Last N turns for context

# Testing
CONVERSATION_TEST_DIR = "QUESTIONS/conversations"
CONVERSATION_STOP_ON_FAIL = True
MIN_CONTEXT_RESOLUTION_RATE = 0.95
```

### Environment Variable

```bash
# Enable conversational mode
export CONVERSATIONAL_MODE=true

# Or disable (default)
export CONVERSATIONAL_MODE=false
```

### Graph Builder with Feature Flag

```python
# chatbot/graph/builder.py

from chatbot import config

def build_graph(checkpointer=None):
    """Build RAG graph - stateless or conversational based on config."""
    
    if config.CONVERSATIONAL_MODE:
        return _build_conversational_graph(checkpointer)
    else:
        return _build_stateless_graph()


def _build_stateless_graph():
    """Original stateless pipeline."""
    workflow = StateGraph(RAGState)
    
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)
    
    workflow.add_edge(START, "classify")
    workflow.add_conditional_edges("classify", route_by_intent, {...})
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)
    workflow.add_edge("location", END)
    
    return workflow.compile()  # No checkpointer


def _build_conversational_graph(checkpointer=None):
    """Conversational pipeline with memory."""
    from langgraph.checkpoint.memory import InMemorySaver
    
    workflow = StateGraph(ConversationalRAGState)
    
    workflow.add_node("reformulate", reformulate_node)  # NEW
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)
    
    workflow.add_edge(START, "reformulate")  # Entry point differs
    workflow.add_edge("reformulate", "classify")
    workflow.add_conditional_edges("classify", route_by_intent, {...})
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)
    workflow.add_edge("location", END)
    
    if checkpointer is None:
        checkpointer = InMemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)
```

### Chatbot Interface with Feature Flag

```python
# chatbot/chatbot.py

class TexasChildcareChatbot:
    """RAG chatbot - stateless or conversational based on config."""
    
    def __init__(self):
        if config.CONVERSATIONAL_MODE:
            from .memory import MemoryManager
            self.memory = MemoryManager(backend=config.MEMORY_BACKEND)
            self.graph = build_graph(checkpointer=self.memory.checkpointer)
        else:
            self.memory = None
            self.graph = build_graph()
    
    def ask(
        self, 
        question: str, 
        thread_id: str | None = None,
        debug: bool = False
    ) -> dict:
        """Ask a question.
        
        Args:
            question: User's question
            thread_id: Conversation thread (ignored if not conversational)
            debug: Enable debug output
        """
        if config.CONVERSATIONAL_MODE:
            return self._ask_conversational(question, thread_id, debug)
        else:
            return self._ask_stateless(question, debug)
    
    def _ask_stateless(self, question: str, debug: bool) -> dict:
        """Original single-turn behavior."""
        input_state = {"query": question, "debug": debug}
        final_state = self.graph.invoke(input_state)
        
        return {
            "answer": final_state["answer"],
            "sources": final_state["sources"],
            "response_type": final_state["response_type"],
        }
    
    def _ask_conversational(
        self, question: str, thread_id: str | None, debug: bool
    ) -> dict:
        """Multi-turn with memory."""
        import uuid
        from langchain_core.messages import HumanMessage
        
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        config = self.memory.get_thread_config(thread_id)
        
        input_state = {
            "messages": [HumanMessage(content=question)],
            "query": question,
            "debug": debug,
        }
        
        final_state = self.graph.invoke(input_state, config)
        turn_count = len(final_state.get("messages", [])) // 2
        
        return {
            "answer": final_state["answer"],
            "sources": final_state["sources"],
            "thread_id": thread_id,
            "turn_count": turn_count,
            "reformulated_query": final_state.get("reformulated_query"),
            "response_type": final_state["response_type"],
        }
```

### Backward Compatibility

| Aspect | `CONVERSATIONAL_MODE=false` | `CONVERSATIONAL_MODE=true` |
|--------|---------------------------|---------------------------|
| State class | `RAGState` | `ConversationalRAGState` |
| Entry node | `classify` | `reformulate` |
| Checkpointer | None | `InMemorySaver` |
| `thread_id` param | Ignored | Used for memory |
| Response fields | `answer`, `sources`, `response_type` | + `thread_id`, `turn_count`, `reformulated_query` |
| Existing tests | Pass unchanged | Pass unchanged |

---

## Prompts Required

> **See:** [conversational_prompts_design.md](./conversational_prompts_design.md) for full prompt specifications.

| # | Prompt | Purpose | File |
|---|--------|---------|------|
| 1 | **Reformulation** | Transform context-dependent queries into standalone | `conversational/reformulation_prompt.py` |
| 2 | **Intent Classification** | Classify using reformulated query | `conversational/intent_classification_prompt.py` |
| 3 | **Reranking** | Score chunks with conversation context | `conversational/reranking_prompt.py` |
| 4 | **Response Generation** | Generate answers maintaining conversation consistency | `conversational/response_generation_prompt.py` |
| 5 | **Summarizer** | Compress conversation history for context injection | `conversational/summarizer_prompt.py` |
| 6 | **Multi-Turn Judge** | Evaluate responses in conversation context (testing) | `evaluation/prompts/multi_turn_judge_prompt.py` |

**Design Principles:**
- XML tags for structured output and reliable parsing
- Few-shot examples over verbose rules
- Domain context in system prompts
- Stateless/conversational variants for each prompt

---

## Sources

- [MTRAG Benchmark (IBM Research)](https://arxiv.org/abs/2501.03468) - Multi-turn RAG evaluation framework
- [Ragas Multi-Turn Evaluation](https://docs.ragas.io/en/stable/howtos/applications/evaluating_multi_turn_conversations/) - AspectCritic metrics
- [LangGraph Memory Documentation](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/persistence.md) - Checkpointer patterns
- [LangGraph Agentic RAG Tutorial](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/rag/langgraph_agentic_rag.md) - Graph architecture
- [MongoDB Long-Term Memory](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph) - Production memory patterns
- [Evidently AI RAG Evaluation](https://www.evidentlyai.com/llm-guide/rag-evaluation) - Testing best practices
