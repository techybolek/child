# Bedrock Agent Mode Integration

AWS managed RAG using Amazon Bedrock Knowledge Bases with Nova models. Uses a pre-configured Knowledge Base (ID: 371M2G58TV) with OpenSearch Serverless backend.

## Architecture

```
BEDROCK AGENT MODE:
  Query → Bedrock retrieve_and_generate → Knowledge Base → Nova Model → Parse Response

RAG PIPELINE MODE (hybrid/dense):
  Query → Classify → Retrieve → Rerank → Generate
```

**Key Difference**: Bedrock Agent uses AWS managed retrieval (~300 token chunks, dense-only) vs the custom hybrid/reranking pipeline (1000 char chunks, 3-tier context, RRF fusion).

## Core Components

### 1. BedrockKBHandler (`chatbot/handlers/bedrock_kb_handler.py`)

Primary handler using boto3 Bedrock Agent Runtime:

```python
class BedrockKBHandler(BaseHandler):
    def __init__(self, model: str | None = None):
        self.client = boto3.client('bedrock-agent-runtime', region_name=config.AWS_REGION)
        self.model_arn = f"arn:aws:bedrock:{config.AWS_REGION}::foundation-model/{model_id}"
        self._sessions: dict[str, dict] = {}  # Client session → Bedrock session mapping

    def _query_bedrock(self, query: str, session_id: str | None = None) -> dict:
        response = self.client.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': config.BEDROCK_KB_ID,
                    'modelArn': self.model_arn,
                    'generationConfiguration': {
                        'promptTemplate': {'textPromptTemplate': BEDROCK_AGENT_PROMPT + ...}
                    }
                }
            },
            sessionId=bedrock_session_id  # For conversation continuity
        )
```

### 2. Configuration (`chatbot/config.py`)

```python
BEDROCK_KB_ID = os.getenv('BEDROCK_KB_ID', '371M2G58TV')
BEDROCK_AGENT_MODEL = os.getenv('BEDROCK_MODEL', 'nova-micro')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
```

### 3. Available Models

| Model | ID | Description |
|-------|-----|-------------|
| Nova Micro | `nova-micro` | Fast, default |
| Nova Lite | `nova-lite` | Balanced |
| Nova Pro | `nova-pro` | High quality |

## API Integration

### Backend Endpoints

```python
# Models endpoint
GET /api/models/bedrock-agent
→ {"models": [{"id": "nova-micro", "name": "Nova Micro"}, ...], "default": "nova-micro"}

# Chat endpoint
POST /api/chat
{
    "question": "What is TWC?",
    "mode": "bedrock_agent",
    "bedrock_agent_model": "nova-micro"
}
```

### Handler Caching

Handlers cached per session for conversation continuity:
```python
cache_key = f"bedrock_{session_id}"
if cache_key in _conversational_chatbots:
    handler = _conversational_chatbots[cache_key]
else:
    handler = BedrockKBHandler(model=request.bedrock_agent_model)
    _conversational_chatbots[cache_key] = handler
```

## Frontend Integration

### Chat Mode Selector (2x2 grid)

```
┌─────────────┬─────────────┐
│ RAG Pipeline│ OpenAI Agent│
├─────────────┼─────────────┤
│ Vertex Agent│Bedrock Agent│
└─────────────┴─────────────┘
```

### Bedrock Settings Section

- Model dropdown: Nova Micro, Nova Lite, Nova Pro
- Orange info box: "Bedrock Agent mode is always conversational and uses AWS managed RAG with Amazon Bedrock Knowledge Base."
- No streaming toggle (not supported)
- No conversational toggle (always conversational)

## Session Management

Client sessions map to Bedrock sessions:

```python
self._sessions[session_id] = {
    'turn_count': 1,
    'bedrock_session_id': response.get('sessionId')  # Bedrock-generated
}
```

- First call: Bedrock generates session ID, stored in mapping
- Subsequent calls: Pass Bedrock session ID for conversation continuity
- Client always sees their original session ID

## Response Parsing

Output format from prompt:
```
ANSWER:
[Response text]

SOURCES:
- [filename1.pdf]
- [filename2.pdf]
```

Parsed into standard response structure:
```python
{
    'answer': str,
    'sources': [{'doc': str, 'pages': [], 'url': ''}],
    'response_type': 'information',
    'thread_id': session_id,
    'turn_count': int
}
```

## Limitations vs Custom Pipeline

| Feature | Bedrock KB | Custom Pipeline |
|---------|------------|-----------------|
| Embeddings | Titan V2 (dense) | OpenAI + BM25 (hybrid) |
| Chunking | ~300 tokens | 1000 chars + 3-tier context |
| Reranking | None | LLM adaptive |
| Page numbers | Not preserved | Preserved |
| Streaming | Not supported | Supported |

## Testing

```bash
# Handler tests (12 tests)
pytest tests/test_bedrock_kb_handler.py -v

# API integration tests (5 tests)
pytest tests/test_bedrock_kb_integration.py -v

# All Bedrock tests
pytest tests/test_bedrock*.py -v
```

## Files Changed

```
chatbot/config.py                      # +5 lines (config)
chatbot/prompts/__init__.py            # +2 lines (export)
chatbot/prompts/bedrock_agent_prompt.py # NEW (55 lines)
chatbot/handlers/bedrock_kb_handler.py  # NEW (248 lines)
backend/api/models.py                  # +8 lines (types)
backend/api/routes.py                  # +38 lines (routing)
frontend/lib/types.ts                  # +9 lines (types)
frontend/lib/api.ts                    # +7 lines (API)
frontend/components/ChatInterface.tsx  # +12 lines (state)
frontend/components/ModelSettings.tsx  # +58 lines (UI)
tests/test_bedrock_kb_handler.py       # NEW (171 lines)
tests/test_bedrock_kb_integration.py   # NEW (96 lines)
```
