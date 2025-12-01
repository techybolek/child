# Bug: Conversation History Not Persisting Between Requests

## Bug Description

When using conversational mode via the backend API with the same `session_id`, the second request sees "No history" instead of using the conversation context from the first request. The query "what about 5" (intended as a follow-up to "what assistance can a family of 4 expect") is not reformulated and retrieves 0 chunks, returning a fallback response instead of a contextual answer about a family of 5.

**Expected behavior:** Follow-up queries in the same session should have access to conversation history and be reformulated based on context.

**Actual behavior:** Every request creates a new chatbot instance with fresh memory, losing all conversation history between requests.

## Problem Statement

The backend API creates a **new `TexasChildcareChatbot` instance for every request** when `conversational_mode=True`. Since each chatbot instance has its own `MemoryManager` with its own `MemorySaver`, the conversation history from request 1 is stored in instance 1's memory, but request 2 creates instance 2 with a completely empty memory - the history is lost.

## Solution Statement

Maintain a **shared cache of conversational chatbot instances** keyed by `session_id`. When a request arrives with `conversational_mode=True`:
1. Check if a chatbot instance already exists for this `session_id`
2. If yes, reuse it (preserving memory)
3. If no, create a new instance and cache it

This mirrors how the singleton `ChatbotService` preserves state for stateless mode, but extends it to support multiple concurrent conversational sessions.

## Steps to Reproduce

1. Start the backend server: `cd backend && python main.py`
2. Send first request:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "what assistance can a family of 4 expect", "session_id": "test-123", "conversational_mode": true}'
   ```
3. Send follow-up request with same session_id:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "what about 5", "session_id": "test-123", "conversational_mode": true}'
   ```
4. Observe: Second response is a fallback message, not a contextual answer about family of 5.
5. Observe in logs: Both requests show "[Reformulate Node] No history, using original query"

## Root Cause Analysis

In `backend/api/routes.py` lines 175-188:

```python
if needs_custom_instance:
    start_time = time.time()
    chatbot = TexasChildcareChatbot(  # ← NEW INSTANCE every request!
        llm_model=request.llm_model,
        ...
        conversational_mode=request.conversational_mode
    )
    thread_id = session_id if request.conversational_mode else None
    result = chatbot.ask(request.question, thread_id=thread_id)
```

Each time `TexasChildcareChatbot()` is called, it creates a new `MemoryManager` (see `chatbot/chatbot.py` lines 44-48):

```python
if self.conversational_mode:
    from .memory import MemoryManager
    self.memory = MemoryManager()  # ← NEW MEMORY every instance!
    self.graph = build_graph(checkpointer=self.memory.checkpointer)
```

The `thread_id` is passed correctly, but it's meaningless because the memory store itself is fresh - there's nothing to retrieve.

## Relevant Files

### Files to Modify

- **`backend/api/routes.py`** - Contains the `/api/chat` endpoint that creates a new chatbot instance per request. This is where the session-based caching logic needs to be added.

### Files for Reference (no changes needed)

- **`backend/services/chatbot_service.py`** - Shows the singleton pattern used for stateless mode. Can inform the caching approach.
- **`chatbot/chatbot.py`** - Shows how `MemoryManager` is created per instance. Confirms the root cause.
- **`chatbot/memory.py`** - Shows `MemorySaver` is in-memory only. Confirms session cache must be in `routes.py`.
- **`tests/test_backend_api.py`** - Contains the failing test `test_conversational_mode_preserves_history`.

## Step by Step Tasks

### Step 1: Add session-based chatbot cache to routes.py

- Add a module-level dictionary to cache conversational chatbot instances: `_conversational_chatbots: Dict[str, TexasChildcareChatbot] = {}`
- Modify the `chat()` endpoint to check the cache before creating a new instance
- When `conversational_mode=True` and `session_id` exists in cache, reuse the cached instance
- When creating a new instance for conversational mode, store it in the cache
- For non-conversational custom instances (model overrides only), continue creating fresh instances (no caching needed)

Key logic:
```python
# At module level
_conversational_chatbots: Dict[str, TexasChildcareChatbot] = {}

# In chat() function
if request.conversational_mode:
    if session_id in _conversational_chatbots:
        chatbot = _conversational_chatbots[session_id]
    else:
        chatbot = TexasChildcareChatbot(
            llm_model=request.llm_model,
            ...
            conversational_mode=True
        )
        _conversational_chatbots[session_id] = chatbot
    result = chatbot.ask(request.question, thread_id=session_id)
```

### Step 2: Handle model override consistency

- When reusing a cached chatbot, verify that the model overrides match the request
- If model overrides differ from the cached instance, either:
  - Option A (simple): Create a new instance and replace the cached one
  - Option B (strict): Return an error explaining model mismatch
- For simplicity, use Option A - the user's latest model preferences should take effect

### Step 3: Run the existing test to verify the fix

- Execute `pytest tests/test_backend_api.py::TestConversationalMode::test_conversational_mode_preserves_history -v`
- Verify the test passes (follow-up response contains family/income context)
- Verify logs show "[Reformulate Node]" detecting history on the second request

### Step 4: Ensure all backend tests pass

- Run the full backend test suite: `pytest tests/test_backend_api.py -v`
- Verify no regressions in other tests (health, models, chat, validation, headers)

## Validation Commands

Execute every command to validate the bug is fixed with zero regressions.

- `cd /home/tromanow/COHORT/TX && pytest tests/test_backend_api.py::TestConversationalMode::test_conversational_mode_preserves_history -v` - Run the specific failing test to verify the bug is fixed
- `cd /home/tromanow/COHORT/TX && pytest tests/test_backend_api.py -v` - Run all backend API tests to ensure no regressions
- Manual verification via curl (optional):
  ```bash
  # Start server in background
  cd backend && python main.py &

  # First request
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"question": "what assistance can a family of 4 expect", "session_id": "manual-test", "conversational_mode": true}'

  # Follow-up (should show contextual answer about family of 5)
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"question": "what about 5", "session_id": "manual-test", "conversational_mode": true}'
  ```

## Notes

- The cache is in-memory and will be lost on server restart. This is acceptable for the prototype.
- No cleanup mechanism is implemented for stale sessions. In production, consider adding TTL-based expiration.
- The fix is minimal and surgical - only `routes.py` is modified.
- No new dependencies are required.
