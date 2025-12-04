# Plan: Add Vertex AI Agent Support to Chatbot

## Overview

Add a new `vertex_agent` mode to the chatbot that uses Google Vertex AI's RAG capabilities with Gemini models, following the same integration pattern as the existing OpenAI Agent mode.

## Architecture Comparison

| Aspect | OpenAI Agent | Vertex Agent (New) |
|--------|--------------|-------------------|
| SDK | `openai`, `agents` | `vertexai`, `google-cloud-aiplatform` |
| Vector Store | OpenAI Vector Store | Vertex RAG Corpus |
| Model | GPT-4o/5 series | Gemini 2.5 Flash/Pro |
| RAG Tool | `FileSearchTool` | `Tool.from_retrieval()` |
| Auth | `OPENAI_API_KEY` | Google Cloud ADC/Service Account |
| Conversation | Manual history accumulation | `ChatSession` built-in |

## Files to Create/Modify

### 1. Configuration (`chatbot/config.py`)
Add Vertex AI settings:
```python
# ===== VERTEX AI AGENT SETTINGS =====
VERTEX_PROJECT_ID = os.getenv('VERTEX_PROJECT_ID', 'docker-app-20250605')
VERTEX_LOCATION = os.getenv('VERTEX_LOCATION', 'us-west1')
VERTEX_CORPUS_NAME = os.getenv('VERTEX_CORPUS_NAME', 'projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952')
VERTEX_AGENT_MODEL = os.getenv('VERTEX_AGENT_MODEL', 'gemini-2.5-flash')
VERTEX_SIMILARITY_TOP_K = 10
```

### 2. Handler (`chatbot/handlers/vertex_agent_handler.py`)
New handler class following OpenAI pattern:

```python
class VertexAgentHandler(BaseHandler):
    def __init__(self, model: str | None = None):
        # Initialize Vertex AI
        vertexai.init(project=config.VERTEX_PROJECT_ID, location=config.VERTEX_LOCATION)

        # Create RAG retrieval tool
        self.rag_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[rag.RagResource(rag_corpus=config.VERTEX_CORPUS_NAME)],
                    similarity_top_k=config.VERTEX_SIMILARITY_TOP_K,
                ),
            )
        )

        # Create model with tool
        self.model = GenerativeModel(
            model_name=model or config.VERTEX_AGENT_MODEL,
            tools=[self.rag_tool],
            system_instruction=SYSTEM_INSTRUCTION,
        )

        # Thread-scoped chat sessions for conversation
        self._sessions: dict[str, ChatSession] = {}

    def handle(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict
    async def handle_async(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict
```

Key differences from OpenAI handler:
- Uses `ChatSession` for built-in conversation memory (simpler than manual accumulation)
- Uses `GenerativeModel.generate_content()` or `chat.send_message()`
- Response parsing uses same ANSWER/SOURCES regex pattern as OpenAI handler

### 3. Backend Models (`backend/api/models.py`)
Extend `ChatRequest`:
```python
mode: Optional[Literal['rag_pipeline', 'openai_agent', 'vertex_agent']] = Field(...)
vertex_agent_model: Optional[str] = Field(None, description="Model for Vertex Agent mode")
```

### 4. Backend Routes (`backend/api/routes.py`)
Add Vertex Agent handling:

```python
@router.get("/models/vertex-agent")
async def get_vertex_agent_models() -> Dict[str, Any]:
    return {
        "models": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ],
        "default": chatbot_config.VERTEX_AGENT_MODEL
    }

# In chat() endpoint:
if request.mode == 'vertex_agent':
    from chatbot.handlers.vertex_agent_handler import VertexAgentHandler
    cache_key = f"vertex_{session_id}"
    # ... similar caching pattern as OpenAI
```

### 5. Evaluation (`evaluation/vertex_evaluator.py`)
New evaluator following OpenAI pattern:

```python
class VertexAgentEvaluator:
    def __init__(self):
        self.handler = VertexAgentHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        # Same pattern as OpenAIAgentEvaluator
```

### 6. Evaluation Runner (`evaluation/run_evaluation.py`)
Add `vertex` mode:

```python
VALID_MODES = ['hybrid', 'dense', 'openai', 'kendra', 'vertex']

if mode == 'vertex':
    from .vertex_evaluator import VertexAgentEvaluator
    custom_evaluator = VertexAgentEvaluator()
```

### 7. Evaluation Config (`evaluation/config.py`)
Add `'vertex'` to `VALID_MODES` list.

## Implementation Steps

1. **Add dependencies** to `requirements.txt`:
   ```
   google-cloud-aiplatform>=1.50.0
   vertexai>=1.50.0
   ```

2. **Add configuration** to `chatbot/config.py`

3. **Create handler** at `chatbot/handlers/vertex_agent_handler.py`:
   - Initialize Vertex AI SDK
   - Create RAG retrieval tool pointing to corpus
   - Create GenerativeModel with tool and system instruction
   - Implement sync/async handle methods
   - Implement conversation management via ChatSession
   - Parse response for answer and sources

4. **Update backend models** (`backend/api/models.py`):
   - Add `'vertex_agent'` to mode Literal
   - Add `vertex_agent_model` field

5. **Update backend routes** (`backend/api/routes.py`):
   - Add `/models/vertex-agent` endpoint
   - Add `vertex_agent` branch in `/chat` endpoint

6. **Create evaluator** at `evaluation/vertex_evaluator.py`

7. **Update evaluation config** (`evaluation/config.py`):
   - Add `'vertex'` to `VALID_MODES`

8. **Update evaluation runner** (`evaluation/run_evaluation.py`):
   - Add vertex mode import and evaluator selection

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | - | Path to service account JSON |
| `VERTEX_PROJECT_ID` | No | `docker-app-20250605` | GCP project ID |
| `VERTEX_LOCATION` | No | `us-west1` | GCP region |
| `VERTEX_CORPUS_NAME` | No | (existing corpus) | RAG corpus resource name |
| `VERTEX_AGENT_MODEL` | No | `gemini-2.5-flash` | Default Gemini model |

*Or use Application Default Credentials (ADC)

## Response Parsing Strategy

**Decision: Structured prompt only** (same as OpenAI pattern)

Include ANSWER/SOURCES format in system instruction and parse with regex:
```python
def _parse_response(self, output_text: str) -> tuple[str, list]:
    answer_match = re.search(r'ANSWER:\s*\n(.*?)(?=\nSOURCES:|$)', output_text, re.DOTALL)
    sources_match = re.search(r'SOURCES:\s*\n(.*?)$', output_text, re.DOTALL)
    # ... same parsing logic as OpenAI handler
```

## Multi-Turn Conversation

Vertex AI's `ChatSession` handles conversation history automatically:
```python
chat = self.model.start_chat()
response = chat.send_message(query)  # Maintains history
```

This is simpler than OpenAI's manual history accumulation.

## Testing Plan

1. Manual test with existing corpus:
   ```bash
   python -c "from chatbot.handlers.vertex_agent_handler import VertexAgentHandler; h = VertexAgentHandler(); print(h.handle('What is CCS?'))"
   ```

2. Run evaluation:
   ```bash
   python -m evaluation.run_evaluation --mode vertex --limit 5 --debug
   ```

3. Test via backend API:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "What is CCS?", "mode": "vertex_agent"}'
   ```

## Frontend UI Updates

**Decision: Add Vertex Agent to frontend ModelSettings panel**

### Files to modify:

**`frontend/lib/types.ts`**
```typescript
export type ChatMode = 'rag_pipeline' | 'openai_agent' | 'vertex_agent';
```

**`frontend/lib/api.ts`**
- Add `fetchVertexAgentModels()` function
- Update `askQuestion()` to support `vertex_agent` mode

**`frontend/components/ModelSettings.tsx`**
- Add "Vertex Agent" option to mode selector (alongside RAG Pipeline and OpenAI Agent)
- Add Vertex model dropdown when Vertex Agent mode selected
- Fetch available models from `/api/models/vertex-agent`

## Key Decisions Summary

| Decision | Choice |
|----------|--------|
| RAG Corpus | Use existing corpus from GOOGLE_EXPERIMENT |
| Response Parsing | Structured prompt only (ANSWER/SOURCES format) |
| Frontend UI | Add Vertex Agent to ModelSettings panel |

## Documentation

Update `SPECS/DOC/` with `vertex_agent_mode_integration.md` following the pattern of `openai_agent_mode_integration.md`.
