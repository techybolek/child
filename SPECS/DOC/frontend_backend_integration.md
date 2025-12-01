# Frontend-Backend Integration

Next.js frontend (port 3000) ↔ FastAPI backend (port 8000)

## Endpoints

### POST `/api/chat`

```json
// Request
{
  "question": "What is CCS?",
  "session_id": "uuid",
  "provider": "groq",
  "llm_model": "openai/gpt-oss-20b",
  "reranker_model": "openai/gpt-oss-120b",
  "intent_model": "openai/gpt-oss-20b",
  "conversational_mode": true
}

// Response
{
  "answer": "CCS is...",
  "sources": [{"doc": "file.pdf", "page": 5, "url": "..."}],
  "response_type": "information",
  "action_items": [{"type": "link", "url": "...", "label": "...", "description": "..."}],
  "processing_time": 3.24,
  "session_id": "uuid",
  "timestamp": "2025-12-01T15:30:05Z"
}
```

### GET `/api/health`

```json
{"status": "ok", "chatbot_initialized": true, "timestamp": "..."}
```

### GET `/api/models?provider=groq`

```json
{
  "provider": "groq",
  "generators": [{"id": "model-id", "name": "model-id"}],
  "rerankers": [...],
  "classifiers": [...],
  "defaults": {"generator": "...", "reranker": "...", "classifier": "..."}
}
```

## Frontend Files

| File | Purpose |
|------|---------|
| `lib/types.ts` | TypeScript interfaces |
| `lib/api.ts` | `askQuestion()`, `checkHealth()`, `fetchAvailableModels()` |
| `components/ChatInterface.tsx` | Main chat component, state management |
| `components/ModelSettings.tsx` | Settings panel (provider, models, conversational toggle) |

## Backend Modes

**Stateless** (default): Uses singleton chatbot, no memory

**Custom instance**: Created when any override is set (`llm_model`, `provider`, `conversational_mode`, etc.)

## Response Types

- `information` - RAG answer with sources
- `location_search` - Template response with HHS facility search link
