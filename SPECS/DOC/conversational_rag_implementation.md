# Conversational RAG Implementation

Multi-turn conversational RAG system with LangGraph orchestration, query reformulation, and automated testing.

## Architecture Overview

```
CONVERSATIONAL MODE (CONVERSATIONAL_MODE=true):
  REFORMULATE → CLASSIFY → [conditional]
                            ├── RETRIEVE → RERANK → GENERATE → END
                            └── LOCATION → END

STATELESS MODE (default):
  CLASSIFY → [conditional]
             ├── RETRIEVE → RERANK → GENERATE → END
             └── LOCATION → END
```

## Core Components

### 1. State Definition (`chatbot/graph/state.py`)

**ConversationalRAGState** extends RAGState with:
```python
messages: Annotated[list[BaseMessage], add_messages]  # Accumulated history
reformulated_query: str | None                        # Context-aware query
```

The `add_messages` reducer automatically accumulates conversation history across turns.

### 2. Memory Manager (`chatbot/memory.py`)

Thread-scoped conversation memory using LangGraph's `MemorySaver`:

```python
class MemoryManager:
    def __init__(self):
        self.checkpointer = MemorySaver()

    def get_thread_config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}
```

Each `thread_id` maintains isolated conversation state.

### 3. Query Reformulation (`chatbot/graph/nodes/reformulate.py`)

Transforms context-dependent queries into standalone queries:

| Original Query | Reformulated |
|----------------|--------------|
| "How do I apply for it?" | "How do I apply for CCS?" |
| "What about for 4?" | "What is the income limit for a family of 4?" |
| "What are the income limits?" | "What are the income limits?" (unchanged) |

**Heuristic Skip:** Detects standalone queries to avoid unnecessary LLM calls:
- Checks for pronouns: "it", "they", "this", "that"
- Checks for context markers: "what about", "how about", "also"
- Short queries (≤3 words) trigger reformulation

### 4. Chatbot Interface (`chatbot/chatbot.py`)

```python
chatbot = TexasChildcareChatbot()

# Stateless (default)
result = chatbot.ask("What is CCS?")

# Conversational
result = chatbot.ask("What is CCS?", thread_id="user-123")
result = chatbot.ask("How do I apply?", thread_id="user-123")  # Uses context
```

**Conversational Response:**
```python
{
    'answer': str,
    'sources': list[dict],
    'thread_id': str,
    'turn_count': int,
    'reformulated_query': str | None,
    'response_type': str
}
```

## Prompts (`chatbot/prompts/conversational/`)

### Reformulation Prompt

```python
REFORMULATION_SYSTEM = """You reformulate follow-up questions into standalone queries
for a Texas childcare assistance chatbot.

<domain>
Texas childcare programs: CCS, CCMS, Texas Rising Star, PSOC.
Key concepts: SMI, income eligibility, workforce boards, BCY.
</domain>"""

REFORMULATION_USER = """<conversation>
{history}
</conversation>

<current_query>{query}</current_query>

Reformulate the current query to be standalone. If already standalone, return unchanged.

<reformulated_query>"""
```

## Configuration

```python
# chatbot/config.py
CONVERSATIONAL_MODE = os.getenv("CONVERSATIONAL_MODE", "false").lower() == "true"
```

```bash
# Enable conversational mode
export CONVERSATIONAL_MODE=true
```

---

# Conversation Testing Framework

## Test File Format (`QUESTIONS/conversations/*.yaml`)

```yaml
name: "CCS Eligibility Multi-Turn"
description: "Tests income eligibility flow with follow-ups"
domain: "eligibility"

conversation:
  - turn: 1
    user: "What are the income limits for childcare assistance?"
    expected_topics: ["SMI", "income eligibility"]
    min_score: 70

  - turn: 2
    user: "What about for a family of 4?"
    requires_context: true  # Must resolve from turn 1
    expected_answer_contains: ["family of 4", "$"]
    min_score: 70

success_criteria:
  min_average_score: 75
  all_turns_pass: true
  context_resolution_rate: 0.95
```

## Evaluator (`evaluation/conversation_evaluator.py`)

**TurnResult:**
```python
@dataclass
class TurnResult:
    turn_number: int
    user_query: str
    reformulated_query: str | None
    response: str
    factual_accuracy: float      # 1-5
    completeness: float          # 1-5
    context_resolution: float    # 0-1
    coherence: float            # 1-3
    composite_score: float      # 0-100
    passed: bool
```

**ConversationResult:**
```python
@dataclass
class ConversationResult:
    name: str
    thread_id: str
    turns: list[TurnResult]
    average_score: float
    context_resolution_rate: float
    conversation_passed: bool
```

**Composite Scoring:**
- Factual Accuracy: 45%
- Completeness: 30%
- Context Resolution: 15%
- Coherence: 10%

## MultiTurnJudge (`evaluation/multi_turn_judge.py`)

LLM-as-a-Judge scoring with conversation context:

```python
judge = MultiTurnJudge()
scores = judge.score_turn(
    query="How do I apply?",
    reformulated_query="How do I apply for CCS?",
    response="To apply for CCS...",
    expected_topics=["application", "workforce board"],
    requires_context=True,
    previous_turns=[...]
)
```

## Running Evaluations

```bash
# Single conversation
python -m evaluation.run_conversation_eval \
  --conversation ccs_eligibility_conv.yaml --debug

# All conversations
python -m evaluation.run_conversation_eval --mode hybrid --all
```

## Test Files

| File | Purpose |
|------|---------|
| `ccs_eligibility_conv.yaml` | 4-turn income eligibility flow |
| `pronoun_resolution_conv.yaml` | Pronoun/reference resolution |
| `topic_switch_conv.yaml` | Topic switching handling |
| `scenarios/*.yaml` | 6 comprehensive scenarios |

---

# Test Suite (`tests/test_conversational_rag.py`)

## Milestone Structure

### Milestone 1: State + Memory
- `test_memory_persistence` - Memory persists across turns
- `test_thread_isolation` - Threads have isolated state
- `test_stateless_mode_unchanged` - Backward compatibility

### Milestone 2: Query Reformulation
- `test_pronoun_resolution` - "it" → program name
- `test_implicit_context_resolution` - "What about 4?" expanded
- `test_standalone_query_passthrough` - Unchanged if standalone
- `test_first_turn_no_reformulation` - Skips without history

### Milestone 3: Testing Framework
- `test_yaml_parsing` - YAML files parse correctly
- `test_evaluator_runs` - Evaluator executes
- `test_context_metric_calculated` - Metrics computed
- `test_judge_scores_turn` - Judge returns valid scores

### Milestone 4: E2E Integration
- `test_full_conversation_evaluation` - All conversations run
- `test_context_resolution_meets_target` - ≥90% resolution rate
- `test_stateless_evaluation_still_works` - Original tests pass

```bash
# Run all tests
pytest tests/test_conversational_rag.py -v

# Run specific milestone
pytest tests/test_conversational_rag.py::TestMilestone2 -v

# Run scenarios
pytest tests/test_conversational_scenarios.py -v
```

---

# Example Flow

**Turn 1:**
```
User: "What is CCS?"
  → [reformulate] No history → returns original
  → [classify] Intent: information
  → [retrieve] Query: "What is CCS?"
  → [rerank] Score chunks
  → [generate] Response with citations

Response: {answer: "CCS is...", turn_count: 1}
```

**Turn 2:**
```
User: "How do I apply for it?"
  → [reformulate] Detects "it", formats history
    → LLM: "How do I apply for the Child Care Services (CCS) program?"
  → [classify] Intent: information
  → [retrieve] Query: reformulated
  → [rerank] Score chunks
  → [generate] Response using reformulated query

Response: {answer: "To apply...", turn_count: 2,
           reformulated_query: "How do I apply for CCS?"}
```

---

# File Structure

```
chatbot/
├── memory.py                    # MemoryManager
├── chatbot.py                   # Interface with thread_id support
├── graph/
│   ├── state.py                 # ConversationalRAGState
│   ├── builder.py               # Graph building (both modes)
│   └── nodes/
│       └── reformulate.py       # Query reformulation node
└── prompts/
    └── conversational/
        └── reformulation_prompt.py

evaluation/
├── conversation_evaluator.py    # Multi-turn evaluator
├── multi_turn_judge.py          # LLM judge
├── run_conversation_eval.py     # CLI runner
└── prompts/
    └── multi_turn_judge_prompt.py

QUESTIONS/conversations/
├── ccs_eligibility_conv.yaml
├── pronoun_resolution_conv.yaml
├── topic_switch_conv.yaml
└── scenarios/                   # 6 scenario files

tests/
├── test_conversational_rag.py   # Milestone tests
└── test_conversational_scenarios.py
```

---

# Key Metrics

| Metric | Target |
|--------|--------|
| Context Resolution Rate | ≥95% |
| Min Pass Score | 70/100 |
| Excellent Score | ≥85/100 |

---

# Design References

- Original spec: `SPECS/conversational_rag_design.md`
- Prompts spec: `SPECS/conversational_prompts_design.md`
- LangGraph pipeline: `SPECS/DOC/langgraph_conversational_pipeline.md`
