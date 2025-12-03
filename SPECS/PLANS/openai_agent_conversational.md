# Plan: Add Conversational Support to OpenAI Agent Handler

## Problem
The `OpenAIAgentHandler` is stateless - it creates a fresh `conversation_history` each call and discards it after response. The experimental `agent-interactive.py` shows the correct pattern: accumulate history across turns using `result.new_items`.

## Goal
Make OpenAI agent fully conversational like the experimental version, with a basic test similar to `test_conversational_scenarios_quick.py`.

---

## Files to Modify

### 1. `chatbot/handlers/openai_agent_handler.py`

**Changes:**
1. Add `_conversations: Dict[str, list]` for thread-scoped storage
2. Add `thread_id` parameter to `handle()` and `_run_agent()`
3. Accumulate history: `conversation_history.extend([item.to_input_item() for item in result.new_items])`
4. Add helper methods: `new_conversation()`, `get_history()`, `clear_conversation()`

**Key Pattern (from experimental):**
```python
# Load existing history
conversation_history = self._conversations.get(thread_id, [])

# Add user message
conversation_history.append({
    "role": "user",
    "content": [{"type": "input_text", "text": query}]
})

# Run agent
result = await Runner.run(self.agent, input=conversation_history, ...)

# Accumulate response
conversation_history.extend([item.to_input_item() for item in result.new_items])

# Save
self._conversations[thread_id] = conversation_history
```

### 2. `chatbot/handlers/base.py`

**Changes:**
- Update `handle()` signature to include optional `thread_id: str | None = None`

### 3. `tests/test_openai_conversational.py` (NEW FILE)

**Structure (similar to test_conversational_scenarios_quick.py):**
```python
class TestOpenAIAgentConversational:
    @pytest.fixture
    def handler(self):
        return OpenAIAgentHandler()

    def test_single_turn(self, handler):
        """Single query works"""
        result = handler.handle("What is CCS?")
        assert "answer" in result

    def test_multi_turn_context(self, handler):
        """Follow-up queries use context"""
        thread_id = handler.new_conversation()

        result1 = handler.handle("What are CCS eligibility criteria?", thread_id=thread_id)
        result2 = handler.handle("What about income limits?", thread_id=thread_id)

        history = handler.get_history(thread_id)
        assert len(history) >= 4  # 2 user + 2 assistant

    def test_conversation_isolation(self, handler):
        """Different threads don't share history"""
        thread1 = handler.new_conversation()
        thread2 = handler.new_conversation()

        handler.handle("What is TANF?", thread_id=thread1)
        handler.handle("What is CCS?", thread_id=thread2)

        assert len(handler.get_history(thread1)) == 2
        assert len(handler.get_history(thread2)) == 2
```

---

## Implementation Steps

### Step 1: Update Handler Signature
- Add `thread_id: str | None = None` to `handle()` method
- Update `base.py` if needed for interface consistency

### Step 2: Add Conversation Storage
```python
def __init__(self):
    # ... existing code ...
    self._conversations: Dict[str, list] = {}
```

### Step 3: Modify `_run_agent()` to Accept thread_id
```python
async def _run_agent(self, query: str, thread_id: str | None = None) -> dict:
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    # Load or init
    conversation_history = self._conversations.get(thread_id, [])

    # Add user message
    conversation_history.append({
        "role": "user",
        "content": [{"type": "input_text", "text": query}]
    })

    # Run agent
    result = await Runner.run(self.agent, input=conversation_history, ...)

    # Accumulate (KEY CHANGE)
    conversation_history.extend([item.to_input_item() for item in result.new_items])

    # Save
    self._conversations[thread_id] = conversation_history

    return {
        "output_text": result.final_output_as(str),
        "thread_id": thread_id,
        "turn_count": len([m for m in conversation_history if m["role"] == "user"])
    }
```

### Step 4: Add Helper Methods
```python
def new_conversation(self) -> str:
    """Start new conversation, return thread_id"""
    return str(uuid.uuid4())

def get_history(self, thread_id: str) -> list[dict]:
    """Get conversation history"""
    history = self._conversations.get(thread_id, [])
    return [
        {"role": item["role"], "content": item["content"][0]["text"] if item["content"] else ""}
        for item in history
    ]

def clear_conversation(self, thread_id: str) -> None:
    """Clear conversation history"""
    self._conversations.pop(thread_id, None)
```

### Step 5: Update `handle()` Return Value
```python
return {
    'answer': answer,
    'sources': sources,
    'response_type': 'information',
    'action_items': [],
    'thread_id': thread_id,      # NEW
    'turn_count': turn_count,    # NEW
}
```

### Step 6: Create Test File
Create `tests/test_openai_conversational.py` with 3 tests:
- `test_single_turn` - Basic functionality
- `test_multi_turn_context` - History accumulation
- `test_conversation_isolation` - Thread isolation

---

## Not In Scope (Future)
- Backend API integration (`/chat` endpoint routing to OpenAI handler)
- ConversationEvaluator integration for OpenAI agent
- Persistent storage (file/DB) - using in-memory dict only
- Session cleanup/TTL

---

## Verification

### New Tests
```bash
pytest tests/test_openai_conversational.py -v
```

### Regression Tests (Must Pass After Changes)

**Handler/Base Interface:**
```bash
pytest tests/test_evaluation_e2e_openai.py -v   # OpenAI agent evaluation (stateless)
pytest tests/test_evaluation_e2e.py -v          # Hybrid mode evaluation
```

**Conversational Mode (Existing - Should NOT Break):**
```bash
pytest tests/test_conversational_rag.py -v      # Core conversational tests
pytest tests/test_conversational_scenarios_quick.py -v  # Quick scenario tests
```

**Backend API:**
```bash
pytest tests/test_backend_api.py -v             # API endpoints
```

**Full Regression Suite:**
```bash
pytest tests/ -v --ignore=tests/test_conversational_scenarios_full.py
```

---

## Existing Test Files Reference

| Test File | Purpose | Affected? |
|-----------|---------|-----------|
| `tests/test_evaluation_e2e_openai.py` | OpenAI agent evaluation (stateless) | Yes - must still work |
| `tests/test_evaluation_e2e.py` | Hybrid mode e2e | No |
| `tests/test_conversational_rag.py` | LangGraph conversational tests | No |
| `tests/test_conversational_scenarios_quick.py` | Conversational scenarios | No |
| `tests/test_backend_api.py` | Backend API tests | No (OpenAI not in API yet) |
| `tests/test_hybrid_retriever.py` | Hybrid retriever | No |
| `tests/test_kendra_retriever.py` | Kendra retriever | No |
| `test_chatbot.py` | Root chatbot test | No |

---

## After Approval: Save Plan

Copy this plan to persistent storage:
```bash
cp /home/tromanow/.claude/plans/humble-strolling-blossom.md /home/tromanow/COHORT/TX/SPECS/PLANS/openai_agent_conversational.md
```
