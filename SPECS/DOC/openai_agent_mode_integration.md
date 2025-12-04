# OpenAI Agent Mode Integration

Agentic RAG using OpenAI Assistants API with FileSearch tool. The agent autonomously reasons and retrieves from a pre-populated vector store.

## Architecture

```
OPENAI AGENT MODE:
  Query → Agent (reasoning tokens) → FileSearch (black-box) → Synthesize → Parse Response

RAG PIPELINE MODE (hybrid/dense):
  Query → Classify → Retrieve → Rerank → Generate
```

**Key Difference**: Agent autonomously decides when/what to search vs deterministic pipeline stages.

## Core Components

### 1. OpenAIAgentHandler (`chatbot/handlers/openai_agent_handler.py`)

Primary handler using OpenAI Agents SDK:

```python
from agents import Agent, FileSearchTool, ModelSettings, Runner, RunConfig

class OpenAIAgentHandler(BaseHandler):
    def __init__(self, model: str | None = None):
        self.model = model or config.OPENAI_AGENT_MODEL

        # FileSearchTool connects to pre-loaded vector store
        self.file_search = FileSearchTool(
            vector_store_ids=[config.OPENAI_VECTOR_STORE_ID]
        )

        # Agent with reasoning support
        self.agent = Agent(
            name="Tx Childcare RAG",
            instructions=self._get_instructions,  # Dynamic prompt
            model=self.model,
            tools=[self.file_search],
            model_settings=ModelSettings(
                store=True,                       # Conversation memory
                reasoning=Reasoning(effort="low") # Extended thinking
            )
        )

        # Thread-scoped conversation storage
        self._conversations: dict[str, list[TResponseInputItem]] = {}
```

### 2. Dynamic Instructions

Agent receives structured prompt with user query injected at runtime:

```python
def _get_instructions(self, run_context, _agent) -> str:
    query = run_context.context.query
    return f"""Concisely answer user questions about Texas childcare assistance...

Output format:
ANSWER:
[Your 1-4 sentence response here]

SOURCES:
- [filename1.pdf]
- [filename2.pdf]

User query: {query}"""
```

### 3. Async Workflow

```python
async def _run_agent(self, query: str, thread_id: str | None = None) -> dict:
    thread_id = thread_id or str(uuid.uuid4())
    conversation_history = self._conversations.get(thread_id, [])

    # Add user message
    conversation_history.append({
        "role": "user",
        "content": [{"type": "input_text", "text": query}]
    })

    # Run agent
    result = await Runner.run(
        self.agent,
        input=conversation_history,
        run_config=RunConfig(trace_metadata={"__trace_source__": "chatbot-handler"}),
        context=QueryContext(query)
    )

    # Accumulate agent response for multi-turn
    conversation_history.extend([item.to_input_item() for item in result.new_items])
    self._conversations[thread_id] = conversation_history

    return {
        "output_text": result.final_output_as(str),
        "thread_id": thread_id,
        "turn_count": sum(1 for item in conversation_history if item.get("role") == "user")
    }
```

### 4. Response Parsing

Regex-based extraction of structured output:

```python
def _parse_response(self, output_text: str) -> tuple[str, list]:
    answer_match = re.search(r'ANSWER:\s*\n(.*?)(?=\nSOURCES:|$)', output_text, re.DOTALL)
    sources_match = re.search(r'SOURCES:\s*\n(.*?)$', output_text, re.DOTALL)

    # Extract sources (filenames only, no page numbers)
    sources = []
    if sources_match:
        for line in sources_match.group(1).strip().split('\n'):
            if line.startswith('- ') and line != '- None':
                doc_name = line[2:].strip().strip('[]')
                sources.append({'doc': doc_name, 'page': 'N/A', 'url': ''})

    return answer, sources
```

### 5. Sync/Async Interfaces

```python
# Sync (for evaluation/CLI)
def handle(self, query: str, thread_id: str | None = None, debug: bool = False) -> dict:
    result = asyncio.run(self._run_agent(query, thread_id))
    answer, sources = self._parse_response(result['output_text'])
    return {'answer': answer, 'sources': sources, 'response_type': 'information', ...}

# Async (for FastAPI)
async def handle_async(self, query: str, thread_id: str | None = None, ...) -> dict:
    result = await self._run_agent(query, thread_id)
    # ... same parsing ...
```

## Configuration

**File**: `chatbot/config.py`

```python
OPENAI_VECTOR_STORE_ID = os.getenv('OPENAI_VECTOR_STORE_ID', 'vs_69210129c50c81919a906d0576237ff5')
OPENAI_AGENT_MODEL = os.getenv('OPENAI_AGENT_MODEL', 'gpt-5-nano')
```

**Environment Variables**:
| Variable | Required | Default |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | - |
| `OPENAI_VECTOR_STORE_ID` | No | `vs_69210129c50c81919a906d0576237ff5` |
| `OPENAI_AGENT_MODEL` | No | `gpt-5-nano` |

**Available Models**: `gpt-4o-mini`, `gpt-4o`, `gpt-5-nano`, `gpt-5-mini`, `gpt-5`

## Vector Store

**Pre-populated externally** - no upload mechanism in this codebase.

Setup:
1. Upload PDFs to OpenAI separately
2. OpenAI creates vector store ID
3. Configure `OPENAI_VECTOR_STORE_ID`
4. `FileSearchTool` references existing store

## Backend API Integration

**File**: `backend/api/routes.py`

### Models Endpoint
```python
@router.get("/models/openai-agent")
async def get_openai_agent_models():
    return {
        "models": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-5-nano", "name": "GPT-5 Nano"},
            # ...
        ],
        "default": config.OPENAI_AGENT_MODEL
    }
```

### Chat Endpoint
```python
@router.post("/chat")
async def chat(request: ChatRequest):
    if request.mode == 'openai_agent':
        # Cache handler per session for conversation continuity
        cache_key = f"openai_{session_id}"
        if cache_key not in _conversational_chatbots:
            _conversational_chatbots[cache_key] = OpenAIAgentHandler(
                model=request.openai_agent_model
            )

        handler = _conversational_chatbots[cache_key]
        result = await handler.handle_async(request.question, thread_id=session_id)
```

### Request Model
```python
class ChatRequest(BaseModel):
    mode: Optional[Literal['rag_pipeline', 'openai_agent']] = None
    openai_agent_model: Optional[str] = None  # e.g., 'gpt-5-nano'
```

## Evaluation Framework

### OpenAIAgentEvaluator (`evaluation/openai_evaluator.py`)

```python
class OpenAIAgentEvaluator:
    def __init__(self):
        self.handler = OpenAIAgentHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        return self.handler.handle(question, debug=debug)
```

### Integration (`evaluation/run_evaluation.py`)

```python
if mode == 'openai':
    from .openai_evaluator import OpenAIAgentEvaluator
    custom_evaluator = OpenAIAgentEvaluator()
```

### Usage
```bash
python -m evaluation.run_evaluation --mode openai
python -m evaluation.run_evaluation --mode openai --limit 5 --debug
python -m evaluation.run_evaluation --mode openai --resume
```

**Output**: `results/openai/RUN_<timestamp>/`

## Multi-Turn Conversation

Handler accumulates conversation history per thread:

```python
# Turn 1
result = handler.handle("What is CCS?", thread_id="user-123")
# → Agent sees: [user: "What is CCS?"]

# Turn 2
result = handler.handle("How do I apply for it?", thread_id="user-123")
# → Agent sees: [user: "What is CCS?", assistant: "CCS is...", user: "How do I apply for it?"]
```

**Conversation Management**:
```python
handler.new_conversation()           # Returns new thread_id
handler.get_history(thread_id)       # Returns simplified history
handler.clear_conversation(thread_id) # Clears thread history
```

**Note**: In-memory storage only - conversations lost on restart.

## Mode Comparison

| Aspect | Hybrid | Dense | OpenAI Agent | Kendra |
|--------|--------|-------|--------------|--------|
| **Vector Store** | Qdrant | Qdrant | OpenAI | AWS |
| **Pipeline** | Retrieve→Rerank→Generate | Retrieve→Rerank→Generate | Agent autonomous | Retrieve→Generate |
| **Reasoning** | None | None | Extended thinking | None |
| **Latency** | 2-3s | 2-3s | 5-8s | 3-4s |
| **Citations** | Page numbers | Page numbers | Filename only | Page numbers |

## Limitations

1. **No Page Numbers** - Citations include filename only
2. **Black-box Retrieval** - Cannot see what FileSearch retrieved
3. **High Latency** - 5-8s per query (reasoning overhead)
4. **Expensive** - Reasoning token surcharge
5. **No Reranking Control** - Agent decides document relevance
6. **In-Memory Conversations** - Lost on restart
7. **Pre-populated Vector Store** - No upload mechanism

## Data Flow

```
User Query
    ↓
OpenAIAgentHandler.handle() / handle_async()
    ↓
QueryContext injected into dynamic instructions
    ↓
Agent.run(tools=[FileSearchTool], reasoning="low")
    ↓
Agent reasons → calls FileSearch → synthesizes response
    ↓
Response parsing (regex: ANSWER:, SOURCES:)
    ↓
Standardized return: {answer, sources, response_type, thread_id, turn_count}
    ↓
[Evaluation] LLM judge scores → results/openai/RUN_*/
```
