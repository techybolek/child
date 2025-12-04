# Vertex AI Agent Mode Integration

Agentic RAG using Google Vertex AI with Gemini models and RAG retrieval tool. The agent uses a pre-populated RAG corpus for document retrieval.

## Architecture

```
VERTEX AGENT MODE:
  Query → GenerativeModel (Gemini) → RAG Retrieval Tool → Synthesize → Parse Response

RAG PIPELINE MODE (hybrid/dense):
  Query → Classify → Retrieve → Rerank → Generate
```

**Key Difference**: Vertex Agent uses Gemini's native RAG retrieval vs the custom hybrid/reranking pipeline.

## Core Components

### 1. VertexAgentHandler (`chatbot/handlers/vertex_agent_handler.py`)

Primary handler using Vertex AI SDK:

```python
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool, ChatSession

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

        # Create model with tool and system instruction
        self.model = GenerativeModel(
            model_name=model or config.VERTEX_AGENT_MODEL,
            tools=[self.rag_tool],
            system_instruction=SYSTEM_INSTRUCTION,
        )

        # Thread-scoped chat sessions for conversation
        self._sessions: dict[str, ChatSession] = {}
```

### 2. Response Parsing

Same structured output format as OpenAI Agent:

```python
def _parse_response(self, output_text: str) -> tuple[str, list]:
    answer_match = re.search(r'ANSWER:\s*\n(.*?)(?=\nSOURCES:|$)', output_text, re.DOTALL)
    sources_match = re.search(r'SOURCES:\s*\n(.*?)$', output_text, re.DOTALL)
    # Extract answer and sources list
```

### 3. Multi-Turn Conversation

Uses Vertex AI's native `ChatSession` for built-in conversation memory:

```python
def _get_or_create_session(self, thread_id: str) -> ChatSession:
    if thread_id not in self._sessions:
        self._sessions[thread_id] = self.model.start_chat()
    return self._sessions[thread_id]

# Usage
chat = self._get_or_create_session(thread_id)
response = chat.send_message(query)  # History maintained automatically
```

### 4. Sync/Async Interfaces

```python
# Sync (for evaluation/CLI)
def handle(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
    result = self._query_model(query, thread_id)
    answer, sources = self._parse_response(result['output_text'])
    return {'answer': answer, 'sources': sources, 'response_type': 'information', ...}

# Async (for FastAPI)
async def handle_async(self, query: str, thread_id: str | None = None, ...) -> dict:
    result = await self._query_model_async(query, thread_id)
    # ... same parsing ...
```

## Configuration

**File**: `chatbot/config.py`

```python
# ===== VERTEX AI AGENT SETTINGS =====
VERTEX_PROJECT_ID = os.getenv('VERTEX_PROJECT_ID', 'docker-app-20250605')
VERTEX_LOCATION = os.getenv('VERTEX_LOCATION', 'us-west1')
VERTEX_CORPUS_NAME = os.getenv('VERTEX_CORPUS_NAME', 'projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952')
VERTEX_AGENT_MODEL = os.getenv('VERTEX_AGENT_MODEL', 'gemini-2.5-flash')
VERTEX_SIMILARITY_TOP_K = 10
```

**Environment Variables**:
| Variable | Required | Default |
|----------|----------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | - |
| `VERTEX_PROJECT_ID` | No | `docker-app-20250605` |
| `VERTEX_LOCATION` | No | `us-west1` |
| `VERTEX_CORPUS_NAME` | No | (existing corpus) |
| `VERTEX_AGENT_MODEL` | No | `gemini-2.5-flash` |

*Or use Application Default Credentials (ADC)

**Available Models**: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`

## RAG Corpus

**Pre-populated externally** - PDFs uploaded via `GOOGLE_EXPERIMENT/load_pdfs.py`.

Setup:
1. Create RAG corpus: `GOOGLE_EXPERIMENT/gemini-1.py`
2. Upload PDFs: `GOOGLE_EXPERIMENT/load_pdfs.py`
3. Configure `VERTEX_CORPUS_NAME` environment variable
4. RAG retrieval tool references existing corpus

## Backend API Integration

**File**: `backend/api/routes.py`

### Models Endpoint
```python
@router.get("/models/vertex-agent")
async def get_vertex_agent_models():
    return {
        "models": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ],
        "default": config.VERTEX_AGENT_MODEL
    }
```

### Chat Endpoint
```python
@router.post("/chat")
async def chat(request: ChatRequest):
    if request.mode == 'vertex_agent':
        from chatbot.handlers.vertex_agent_handler import VertexAgentHandler

        # Cache handler per session for conversation continuity
        cache_key = f"vertex_{session_id}"
        if cache_key not in _conversational_chatbots:
            _conversational_chatbots[cache_key] = VertexAgentHandler(
                model=request.vertex_agent_model
            )

        handler = _conversational_chatbots[cache_key]
        result = await handler.handle_async(request.question, thread_id=session_id)
```

### Request Model
```python
class ChatRequest(BaseModel):
    mode: Optional[Literal['rag_pipeline', 'openai_agent', 'vertex_agent']] = None
    vertex_agent_model: Optional[str] = None  # e.g., 'gemini-2.5-flash'
```

## Evaluation Framework

### VertexAgentEvaluator (`evaluation/vertex_evaluator.py`)

```python
class VertexAgentEvaluator:
    def __init__(self):
        self.handler = VertexAgentHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        return self.handler.handle(question, debug=debug)
```

### Integration (`evaluation/run_evaluation.py`)

```python
if mode == 'vertex':
    from .vertex_evaluator import VertexAgentEvaluator
    custom_evaluator = VertexAgentEvaluator()
```

### Usage
```bash
python -m evaluation.run_evaluation --mode vertex
python -m evaluation.run_evaluation --mode vertex --limit 5 --debug
python -m evaluation.run_evaluation --mode vertex --resume
```

**Output**: `results/vertex/RUN_<timestamp>/`

## Frontend Integration

### Types (`frontend/lib/types.ts`)
```typescript
export type ChatMode = 'rag_pipeline' | 'openai_agent' | 'vertex_agent'

export const VERTEX_AGENT_MODELS = [
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro' },
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
] as const

export interface ChatRequest {
  // ...
  vertex_agent_model?: string
}
```

### API Client (`frontend/lib/api.ts`)
```typescript
export async function fetchVertexAgentModels(): Promise<{ models: Model[]; default: string }> {
  const response = await fetch(`${API_BASE_URL}/api/models/vertex-agent`)
  return response.json()
}
```

### Model Settings (`frontend/components/ModelSettings.tsx`)
- Three-way mode selector: RAG Pipeline | OpenAI Agent | Vertex Agent
- Gemini model dropdown when Vertex Agent mode selected

## Mode Comparison

| Aspect | Hybrid | Dense | OpenAI Agent | Vertex Agent |
|--------|--------|-------|--------------|--------------|
| **Vector Store** | Qdrant | Qdrant | OpenAI | Vertex RAG Corpus |
| **Model** | Groq/OpenAI | Groq/OpenAI | GPT-4o/5 | Gemini 2.5 |
| **Pipeline** | Retrieve→Rerank→Generate | Retrieve→Rerank→Generate | Agent autonomous | RAG Tool + Generate |
| **Citations** | Page numbers | Page numbers | Filename only | Filename only |

## Limitations

1. **No Page Numbers** - Citations include filename only (same as OpenAI Agent)
2. **External Corpus Setup** - RAG corpus must be pre-populated via GOOGLE_EXPERIMENT scripts
3. **Google Cloud Auth** - Requires service account or ADC setup
4. **In-Memory Sessions** - Conversation sessions lost on restart

## Data Flow

```
User Query
    ↓
VertexAgentHandler.handle() / handle_async()
    ↓
Get or create ChatSession for thread_id
    ↓
GenerativeModel.send_message() with RAG retrieval tool
    ↓
Gemini retrieves from corpus → generates response
    ↓
Response parsing (regex: ANSWER:, SOURCES:)
    ↓
Standardized return: {answer, sources, response_type, thread_id, turn_count}
    ↓
[Evaluation] LLM judge scores → results/vertex/RUN_*/
```
