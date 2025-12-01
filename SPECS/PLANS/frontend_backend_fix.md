# Plan: Fix Frontend/Backend Integration

## Summary
Full health check and fixes for the Texas Childcare RAG web application:
1. Make model selection actually work (currently fake)
2. Wire up conversational mode with user toggle
3. Verify end-to-end functionality

**Constraint:** CLI (`interactive_chat.py`) must remain unchanged and use env var behavior.

---

## Phase 1: Fix Model Selection Regression

**Problem:** Model selection worked before LangGraph migration but broke during refactor. The `chatbot.py` constructor accepts `llm_model`, `reranker_model`, `intent_model`, `provider` but no longer passes them to the pipeline. Previously, `IntentRouter` received these params; now the LangGraph nodes read directly from config.

**Solution:** Pass model overrides through LangGraph state so nodes can check for overrides before falling back to config.

### Files to Modify:

**1. `chatbot/chatbot.py`**
- Store model params in `__init__`: `self.llm_model`, `self.reranker_model`, `self.intent_model`, `self.provider`
- Add override fields to `initial_state` in `_ask_stateless()` and `_ask_conversational()`:
  ```python
  "llm_model_override": self.llm_model,
  "reranker_model_override": self.reranker_model,
  "intent_model_override": self.intent_model,
  "provider_override": self.provider,
  ```

**2. `chatbot/graph/nodes/generate.py`**
- Check state for overrides before using config:
  ```python
  provider = state.get("provider_override") or config.LLM_PROVIDER
  model = state.get("llm_model_override") or config.LLM_MODEL
  ```

**3. `chatbot/graph/nodes/rerank.py`**
- Same pattern:
  ```python
  provider = state.get("provider_override") or config.RERANKER_PROVIDER
  model = state.get("reranker_model_override") or config.RERANKER_MODEL
  ```

**4. `chatbot/graph/nodes/classify.py`**
- Same pattern:
  ```python
  provider = state.get("provider_override") or config.INTENT_CLASSIFIER_PROVIDER
  model = state.get("intent_model_override") or config.INTENT_CLASSIFIER_MODEL
  ```

---

## Phase 2: Wire Up Conversational Mode

**Problem:** Chatbot uses `config.CONVERSATIONAL_MODE` env var at init time. User wants per-request toggle in UI while CLI stays unchanged.

**Solution:** Add optional `conversational_mode` param to `__init__` that overrides env var when explicitly set.

### Chatbot Changes:

**1. `chatbot/chatbot.py`**
- Add `conversational_mode` parameter to `__init__`:
  ```python
  def __init__(self, llm_model=None, reranker_model=None, intent_model=None,
               provider=None, conversational_mode=None):
      # Explicit param takes precedence, otherwise use env var
      use_conversational = (conversational_mode
                            if conversational_mode is not None
                            else config.CONVERSATIONAL_MODE)

      if use_conversational:
          from .memory import MemoryManager
          self.memory = MemoryManager()
          self.graph = build_graph(checkpointer=self.memory.checkpointer)
      else:
          self.memory = None
          self.graph = build_graph()
  ```

**CLI unchanged:** `TexasChildcareChatbot()` → uses env var (no explicit param)
**Web backend:** `TexasChildcareChatbot(conversational_mode=True)` → explicitly enables

### Backend Changes:

**2. `backend/api/models.py`**
- Add to `ChatRequest`:
  ```python
  conversational_mode: Optional[bool] = Field(False, description="Enable conversational memory")
  ```

**3. `backend/api/routes.py`**
- Create chatbot with `conversational_mode=True` when user enables toggle
- Pass `thread_id=request.session_id` when conversational mode enabled:
  ```python
  chatbot = TexasChildcareChatbot(
      llm_model=request.llm_model,
      conversational_mode=request.conversational_mode  # NEW
  )
  thread_id = request.session_id if request.conversational_mode else None
  result = chatbot.ask(request.question, thread_id=thread_id)
  ```

**4. `backend/services/chatbot_service.py`**
- The singleton pattern complicates this. Options:
  - A) Create new chatbot instance when conversational_mode=True (simpler)
  - B) Always init singleton with memory, control via thread_id (requires singleton change)
- **Recommend Option A:** When `request.conversational_mode=True`, skip singleton and create fresh instance.

### Frontend Changes:

**5. `frontend/lib/types.ts`**
- Add to `ChatRequest`:
  ```typescript
  conversational_mode?: boolean
  ```

**6. `frontend/lib/api.ts`**
- Add `conversationalMode` parameter to `askQuestion()` and include in request body

**7. `frontend/components/ModelSettings.tsx`**
- Add props: `conversationalMode: boolean`, `onConversationalModeChange: (enabled: boolean) => void`
- Add checkbox toggle UI

**8. `frontend/components/ChatInterface.tsx`**
- Add state: `const [conversationalMode, setConversationalMode] = useState(false)`
- Pass to `askQuestion()` and `<ModelSettings />`

---

## Phase 3: Health Check Verification

1. Start backend: `cd backend && python main.py`
2. Test health: `curl http://localhost:8000/api/health`
3. Start frontend: `cd frontend && npm run dev`
4. Test in browser at http://localhost:3000
5. Test model selection and conversational toggle
6. Verify CLI still works: `python interactive_chat.py`

---

## Implementation Order

1. **Chatbot core** - Add `conversational_mode` param to `__init__`, store model params, add to state
2. **Graph nodes** - Check state overrides in classify, rerank, generate
3. **Backend API** - Add `conversational_mode` field, handle in routes
4. **Frontend types** - Add `conversational_mode` field
5. **Frontend API** - Pass `conversationalMode` parameter
6. **Frontend UI** - Add toggle to ModelSettings, wire in ChatInterface
7. **End-to-end test** - Verify all works together
8. **CLI regression test** - Verify `interactive_chat.py` unchanged

---

## Critical Files

| File | Changes |
|------|---------|
| `chatbot/chatbot.py` | Add `conversational_mode` param, store model params, add to initial_state |
| `chatbot/graph/nodes/generate.py` | Check state overrides |
| `chatbot/graph/nodes/rerank.py` | Check state overrides |
| `chatbot/graph/nodes/classify.py` | Check state overrides |
| `backend/api/models.py` | Add `conversational_mode` field |
| `backend/api/routes.py` | Pass `conversational_mode` to chatbot, `thread_id` conditionally |
| `frontend/lib/types.ts` | Add `conversational_mode` |
| `frontend/lib/api.ts` | Add `conversationalMode` parameter |
| `frontend/components/ModelSettings.tsx` | Add toggle UI |
| `frontend/components/ChatInterface.tsx` | Add state, wire toggle |
