# Plan: OpenAI Agent Mode UI Selection

## Summary
Add mode selector to chat UI allowing users to switch between "RAG Pipeline" and "OpenAI Agent" modes, with contextual settings for each mode.

## Current State
- **Backend**: Only routes to `TexasChildcareChatbot` (RAG pipeline)
- **OpenAI Agent Handler**: Exists at `chatbot/handlers/openai_agent_handler.py`, uses **OpenAI Agents SDK** (not deprecated Assistants API) with `FileSearchTool`
- **Config**: `OPENAI_VECTOR_STORE_ID` has hardcoded default in config (no env var required), `OPENAI_AGENT_MODEL` defaults to `gpt-5-nano`
- **Handler limitation**: Constructor accepts no parameters - model is hardcoded from config

## Step 0: Update Spec File (`SPECS/REQUESTS/openai-agent-mode-ui-2025-12-03.md`)

The spec has inaccuracies that need correction:

| Section | Line | Current (Wrong) | Corrected |
|---------|------|-----------------|-----------|
| Overview | 7 | "Assistants API with FileSearch" | "OpenAI Agents SDK with FileSearchTool" |
| Problem Statement | 10 | "OpenAI's Assistants API with FileSearch" | "OpenAI Agents SDK with FileSearchTool" |
| Acceptance Criteria | 38 | gpt-5-nano, gpt-5-mini, gpt-4.1-nano, gpt-4.1-mini, gpt-4.1, gpt-5.1 | gpt-4o-mini, gpt-5-nano, gpt-5-mini, gpt-5 |
| State/Models | 71-78 | Same wrong model list | gpt-4o-mini, gpt-5-nano, gpt-5-mini, gpt-5 |
| Backend File | 84 | `backend/main.py` | `backend/api/routes.py` |
| Request example | 99 | `gpt-4.1-mini` | `gpt-5-nano` |
| Dependencies | 129 | "OpenAI Assistants API integration (existing in evaluation/openai_evaluator.py)" | "OpenAI Agents SDK handler (existing in chatbot/handlers/openai_agent_handler.py)" |
| UI example | 157 | `gpt-4.1-mini` | `gpt-5-nano` |
| Backend routing | 173-184 | Comments say "Assistants API", method `.ask()` | Comments say "Agents SDK", method `.handle(query, thread_id)` |

**Specific edits to spec file:**

1. Line 7: Change "Assistants API with FileSearch" → "OpenAI Agents SDK with FileSearchTool"
2. Line 10: Change "OpenAI's Assistants API with FileSearch" → "OpenAI Agents SDK with FileSearchTool"
3. Line 38: Replace model list with: gpt-4o-mini, gpt-5-nano, gpt-5-mini, gpt-5
4. Lines 71-78: Update OPENAI_AGENT_MODELS array
5. Line 84: Change `backend/main.py` → `backend/api/routes.py`
6. Line 99: Change `gpt-4.1-mini` → `gpt-5-nano`
7. Line 129: Change dependency reference
8. Line 157: Change `gpt-4.1-mini` → `gpt-5-nano`
9. Lines 173-184: Fix backend routing code block

## Changes Required

### 1. Backend: Modify OpenAIAgentHandler (`chatbot/handlers/openai_agent_handler.py`)

Add `model` parameter to constructor:

```python
def __init__(self, model=None):
    """Initialize with optional model override"""
    effective_model = model or config.OPENAI_AGENT_MODEL

    self.file_search = FileSearchTool(
        vector_store_ids=[config.OPENAI_VECTOR_STORE_ID]
    )

    self.agent = Agent(
        name="Tx Childcare RAG",
        instructions=self._get_instructions,
        model=effective_model,  # Use parameter or config
        ...
    )

    self.model = effective_model  # Store for debug info
```

### 2. Backend: Update API Models (`backend/api/models.py`)

Add to `ChatRequest`:
```python
mode: str | None = Field(None, description="Chat mode: 'rag_pipeline' or 'openai_agent'")
openai_agent_model: str | None = Field(None, description="Model for OpenAI Agent mode")
```

### 3. Backend: Update Routes (`backend/api/routes.py`)

Add OpenAI Agent routing in `/api/chat`:
```python
if request.mode == "openai_agent":
    from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler

    # Cache handler per session for conversation continuity
    cache_key = f"openai_{session_id}"
    if cache_key in _conversational_chatbots:
        handler = _conversational_chatbots[cache_key]
    else:
        handler = OpenAIAgentHandler(model=request.openai_agent_model)
        _conversational_chatbots[cache_key] = handler

    result = handler.handle(request.question, thread_id=session_id)
else:
    # Existing RAG pipeline logic
```

Add `/api/models` support for OpenAI Agent models:
```python
@router.get("/models/openai-agent")
async def get_openai_agent_models():
    return {
        "models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-5-nano", "name": "GPT-5 Nano"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini"},
            {"id": "gpt-5", "name": "GPT-5"},
        ],
        "default": "gpt-5-nano"
    }
```

### 4. Frontend: Update Types (`frontend/lib/types.ts`)

```typescript
export type ChatMode = 'rag_pipeline' | 'openai_agent';

export const OPENAI_AGENT_MODELS = [
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'gpt-5-nano', name: 'GPT-5 Nano' },
  { id: 'gpt-5-mini', name: 'GPT-5 Mini' },
  { id: 'gpt-5', name: 'GPT-5' },
];

export interface ChatRequest {
  question: string;
  session_id?: string;
  mode?: ChatMode;
  openai_agent_model?: string;
  // ... existing RAG fields
}
```

### 5. Frontend: Update API (`frontend/lib/api.ts`)

Update `askQuestion()` to include mode and openai_agent_model in request body.

### 6. Frontend: Update ChatInterface (`frontend/components/ChatInterface.tsx`)

- Add `mode` state (default: `'rag_pipeline'`)
- Add `openaiAgentModel` state (default: `'gpt-5-nano'`)
- On mode switch: clear messages, generate new session_id
- Pass mode and model to API calls

### 7. Frontend: Update ModelSettings (`frontend/components/ModelSettings.tsx`)

- Add mode selector (segmented control or tabs)
- Conditional rendering:
  - RAG Pipeline: Show all current settings (provider, models, conversational toggle)
  - OpenAI Agent: Show only GPT model dropdown

## Files to Modify

| File | Change |
|------|--------|
| `SPECS/REQUESTS/openai-agent-mode-ui-2025-12-03.md` | Fix spec inaccuracies (Step 0) |
| `chatbot/handlers/openai_agent_handler.py` | Add `model` parameter to constructor |
| `backend/api/models.py` | Add `mode`, `openai_agent_model` fields |
| `backend/api/routes.py` | Add OpenAI Agent routing, add models endpoint |
| `frontend/lib/types.ts` | Add ChatMode type, OPENAI_AGENT_MODELS |
| `frontend/lib/api.ts` | Update request to include mode |
| `frontend/components/ChatInterface.tsx` | Add mode state, clear on switch |
| `frontend/components/ModelSettings.tsx` | Add mode selector, conditional settings |

## Behavior Summary

- Default mode: RAG Pipeline
- Mode switch clears chat and starts new session
- OpenAI Agent mode: inherently conversational (no toggle needed)
- RAG Pipeline mode: shows all existing settings
- No persistence across page refresh
