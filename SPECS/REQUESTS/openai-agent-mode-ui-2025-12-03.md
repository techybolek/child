# Feature Request: OpenAI Agent Mode UI Selection

**Date:** 2025-12-03
**Status:** Refined

## Overview
Add a top-level mode selector to the chat UI allowing users to switch between "RAG Pipeline" (current behavior) and "OpenAI Agent" (Assistants API with FileSearch). Each mode has distinct configuration options.

## Problem Statement
The application supports two fundamentally different retrieval approaches - the custom RAG pipeline (hybrid/dense search with Qdrant) and OpenAI's Assistants API with FileSearch. Currently, only the RAG pipeline is accessible via the UI. Users need the ability to compare or choose between these approaches.

## Users & Stakeholders
- Primary Users: End users testing/comparing retrieval approaches
- Secondary: Developers evaluating RAG vs OpenAI Agent performance

## Functional Requirements

1. **Mode Selector**: Top-level toggle/selector between "RAG Pipeline" and "OpenAI Agent"
2. **Contextual Settings**: Settings panel shows only relevant options based on selected mode
3. **Auto-clear on Switch**: Switching modes clears chat history and starts fresh session
4. **Default Mode**: RAG Pipeline is the default on page load
5. **No Persistence**: Mode selection resets to default on page refresh

## User Flow

1. User loads the chat UI → RAG Pipeline mode active by default
2. User sees mode selector prominently displayed (above or alongside settings)
3. User clicks to switch to "OpenAI Agent"
4. Chat clears, settings panel updates to show only GPT model selection
5. User selects GPT model and starts conversation
6. User can switch back to "RAG Pipeline" → chat clears, full settings restored

## Acceptance Criteria

- [ ] Mode selector visible with two options: "RAG Pipeline" and "OpenAI Agent"
- [ ] RAG Pipeline mode shows: Provider, LLM Model, Reranker Model, Intent Model, Conversational toggle
- [ ] OpenAI Agent mode shows: GPT Model dropdown only
- [ ] OpenAI Agent GPT models: gpt-5-nano, gpt-5-mini, gpt-4.1-nano, gpt-4.1-mini, gpt-4.1, gpt-5.1
- [ ] Switching modes clears chat history immediately
- [ ] Switching modes starts a new backend session
- [ ] RAG Pipeline is default on page load
- [ ] Mode selection does NOT persist across page refresh
- [ ] OpenAI Agent mode does NOT show conversational toggle (inherently conversational)
- [ ] Chat requests include mode indicator for backend routing

## User Experience

- **Interface**: Web (existing Next.js frontend)
- **Key Interactions**:
  - Mode selector as primary choice (segmented control or prominent dropdown)
  - Settings panel updates contextually based on mode
  - Clear visual distinction between modes
- **Feedback**:
  - Chat clears visibly when switching modes
  - No confirmation dialog needed (switching is non-destructive, just clears current session)

## Technical Requirements

### Frontend Changes

**New/Modified Files:**
- `frontend/lib/types.ts` - Add mode type, OpenAI model list
- `frontend/lib/api.ts` - Update request to include mode
- `frontend/components/ChatInterface.tsx` - Add mode state, clear on switch
- `frontend/components/ModelSettings.tsx` - Conditional rendering based on mode

**State:**
```typescript
type ChatMode = 'rag_pipeline' | 'openai_agent';

const OPENAI_AGENT_MODELS = [
  'gpt-5-nano',
  'gpt-5-mini',
  'gpt-4.1-nano',
  'gpt-4.1-mini',
  'gpt-4.1',
  'gpt-5.1'
];
```

### Backend Changes

**Modified Files:**
- `backend/main.py` - Handle `mode` parameter, route to appropriate handler

**Request Schema Update:**
```json
{
  "question": "...",
  "session_id": "...",
  "mode": "rag_pipeline" | "openai_agent",
  // RAG Pipeline params (ignored if mode=openai_agent)
  "provider": "groq",
  "llm_model": "...",
  "reranker_model": "...",
  "intent_model": "...",
  "conversational_mode": true,
  // OpenAI Agent params (ignored if mode=rag_pipeline)
  "openai_agent_model": "gpt-4.1-mini"
}
```

### Performance
- Mode switching should be instant (client-side state change)
- No additional API calls on mode switch (just clear local state)

### Security
- No new auth requirements
- OpenAI API key already configured server-side

## Data Model

- **Storage**: No new persistent storage
- **Session**: New session_id generated on mode switch
- **Retention**: N/A (no persistence)

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| Switch mode mid-typing | Clear input along with chat history |
| OpenAI API unavailable | Show error message, allow retry |
| Invalid model selection | Fallback to default model for that mode |
| Backend doesn't support mode param | Graceful fallback to RAG pipeline |

## Dependencies

- **Requires**:
  - OpenAI Assistants API integration (existing in `evaluation/openai_evaluator.py`)
  - Backend endpoint update to handle mode routing
- **Blocks**: Nothing

## Out of Scope

- Kendra mode in UI (evaluation-only for now)
- Dense-only mode toggle (subset of RAG pipeline, not user-facing)
- Persisting mode preference
- Side-by-side comparison view
- Streaming responses for OpenAI Agent mode (future enhancement)

## Success Metrics

- Users can successfully switch between modes
- OpenAI Agent responses return correctly
- No regression in RAG Pipeline functionality

## Implementation Notes

### UI Layout Suggestion

```
┌─────────────────────────────────────────┐
│  [RAG Pipeline]  [OpenAI Agent]         │  ← Segmented control
├─────────────────────────────────────────┤
│  Settings (contextual)                  │
│  ┌─────────────────────────────────┐    │
│  │ GPT Model: [gpt-4.1-mini    ▼]  │    │  ← OpenAI Agent: single dropdown
│  └─────────────────────────────────┘    │
│                 OR                       │
│  ┌─────────────────────────────────┐    │
│  │ Provider: [groq ▼]              │    │  ← RAG Pipeline: full settings
│  │ LLM Model: [...]                │    │
│  │ Reranker: [...]                 │    │
│  │ Intent: [...]                   │    │
│  │ [✓] Conversational Mode         │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Backend Routing Logic

```python
# backend/main.py
if request.mode == "openai_agent":
    # Use OpenAI Assistants API
    response = openai_agent_handler.ask(
        question=request.question,
        model=request.openai_agent_model,
        session_id=request.session_id
    )
else:
    # Use existing RAG pipeline
    response = chatbot.ask(...)
```
