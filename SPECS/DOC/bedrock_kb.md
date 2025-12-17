# Amazon Bedrock Knowledge Base Integration

AWS managed RAG using Amazon Bedrock Knowledge Bases with Nova models. Uses a pre-configured Knowledge Base.

## Quick Start

```bash
# Web app - chat with Bedrock Agent mode
cd backend && python main.py      # API on :8000
cd frontend && npm run dev        # UI on :3000
# Select "Bedrock Agent" in chat mode selector

# CLI - evaluation mode
python -m evaluation.run_evaluation --mode bedrock --test --limit 5

# With specific model
BEDROCK_MODEL=nova-pro python -m evaluation.run_evaluation --mode bedrock
```

## Architecture

```
BEDROCK AGENT MODE (Web App):
  Query → BedrockKBHandler → retrieve_and_generate API
       → Knowledge Base (371M2G58TV) → Nova Model
       → Parse Response + Extract Citations → Response

BEDROCK EVALUATION MODE:
  Question → BedrockKBEvaluator → retrieve_and_generate API
          → Knowledge Base → Nova Model
          → Answer + Citations → LLM Judge → Score
```

**Key Difference from Custom Pipeline**: Bedrock Agent uses AWS managed retrieval (~300 token chunks, dense-only) vs the custom hybrid pipeline (1000 char chunks, 3-tier context, RRF fusion, LLM reranking).

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_KB_ID` | `371M2G58TV` | Knowledge Base ID |
| `BEDROCK_MODEL` | `nova-micro` | Generation model |
| `AWS_REGION` | `us-east-1` | AWS region |

### Config Files

```python
# chatbot/config.py
BEDROCK_KB_ID = os.getenv('BEDROCK_KB_ID', '371M2G58TV')
BEDROCK_AGENT_MODEL = os.getenv('BEDROCK_MODEL', 'nova-micro')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
```

## Available Models

### Amazon Models (No Approval Required)

| Short Name | Model ID | Description |
|------------|----------|-------------|
| `nova-micro` | `amazon.nova-micro-v1:0` | Fast, default |
| `nova-lite` | `amazon.nova-lite-v1:0` | Balanced |
| `nova-pro` | `amazon.nova-pro-v1:0` | High quality |
| `titan-express` | `amazon.titan-text-express-v1` | Titan Express |
| `titan-lite` | `amazon.titan-text-lite-v1` | Titan Lite |

### Anthropic Models (May Require Use Case Form)

| Short Name | Model ID | Notes |
|------------|----------|-------|
| `3-haiku` | `anthropic.claude-3-haiku-20240307-v1:0` | Foundation model |
| `3.5-haiku` | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Inference profile |
| `4-5` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Inference profile |

## Knowledge Base Setup

**Knowledge Base ID:** `371M2G58TV`
**Data Source ID:** `V4C2EUGYSY`
**S3 Bucket:** `cohort-tx-1` (28 PDFs)
**Embeddings:** Titan Text Embeddings V2

### Sync Documents

```python
import boto3
client = boto3.client('bedrock-agent', region_name='us-east-1')
client.start_ingestion_job(
    knowledgeBaseId='371M2G58TV',
    dataSourceId='V4C2EUGYSY'
)
```

### Document Metadata (Source URLs)

To enable full clickable source URLs in citations (instead of just filenames), each PDF needs a companion `.metadata.json` file in S3:

**S3 Structure:**
```
s3://cohort-tx-1/
├── wd-24-23-att1-twc.pdf
├── wd-24-23-att1-twc.pdf.metadata.json    ← Metadata file
└── ...
```

**Metadata File Format:**
```json
{
  "metadataAttributes": {
    "source_url": "https://www.twc.texas.gov/sites/default/files/ccel/docs/wd-24-23-att1-twc.pdf"
  }
}
```

**Scripts:**
```bash
cd LOAD_DB

# Generate metadata files from scraper data
python generate_bedrock_metadata.py

# Upload to S3 and resync KB
python upload_bedrock_metadata.py

# Or dry-run first
python upload_bedrock_metadata.py --dry-run
```

After resync, `_extract_citations()` extracts `source_url` from `ref.get('metadata', {}).get('source_url', '')`.

## Components

### 1. BedrockKBHandler (Web App / CLI)

Primary handler for chat interface at `chatbot/handlers/bedrock_kb_handler.py`:

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
                        'promptTemplate': {
                            'textPromptTemplate': BEDROCK_AGENT_PROMPT + '\n\n$output_format_instructions$\n\nQuestion: $query$\n\nSearch results:\n$search_results$'
                        }
                    }
                }
            },
            sessionId=bedrock_session_id  # For conversation continuity
        )
```

**Key Features:**
- Custom prompt template with `BEDROCK_AGENT_PROMPT`
- Session management for multi-turn conversations
- Citation extraction from API response (not LLM text)
- Both sync (`handle`) and async (`handle_async`) methods

### 2. BedrockKBEvaluator (Evaluation Framework)

Evaluator for benchmarking at `evaluation/bedrock_evaluator.py`:

```python
class BedrockKBEvaluator:
    def query(self, question: str, debug: bool = False) -> dict:
        response = self.client.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': self.model_arn
                }
            }
        )
```

**Key Difference:** Evaluator uses default Bedrock prompt (no custom template) for fair comparison with out-of-box AWS RAG.

### 3. Model Resolver

Dynamic model resolution at `evaluation/bedrock_model_resolver.py`:

```python
from evaluation.bedrock_model_resolver import resolve_model_arn

model_id, model_arn, display_name = resolve_model_arn('nova-micro')
# Returns: ('amazon.nova-micro-v1:0', 'arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-micro-v1:0', 'Nova Micro')
```

Handles both foundation models (direct ARN) and inference profiles (requires API lookup).

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

### Chat Mode Selector (2x2 Grid)

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

## Citation Handling

Citations extracted from Bedrock API response (not from LLM text output):

```python
def _extract_citations(self, citations: list) -> list:
    sources = []
    seen_docs = set()

    for citation in citations:
        for ref in citation.get('retrievedReferences', []):
            location = ref.get('location', {})
            s3_loc = location.get('s3Location', {})
            uri = s3_loc.get('uri', '')

            doc_name = uri.split('/')[-1] if uri else ''
            if doc_name and doc_name not in seen_docs:
                seen_docs.add(doc_name)
                sources.append({
                    'doc': doc_name,
                    'pages': [],  # Bedrock KB doesn't preserve page numbers
                    'url': ''
                })
    return sources
```

**Important:** Custom prompts must include `$output_format_instructions$` placeholder for citations to work. See `SPECS/ISSUES/bedrock_missing_citations.md` for details.

## Response Structure

```python
{
    'answer': str,                    # Parsed answer text
    'sources': [                      # From API citations
        {'doc': 'filename.pdf', 'pages': [], 'url': ''}
    ],
    'response_type': 'information',
    'action_items': [],
    'thread_id': session_id,          # Client session ID
    'turn_count': int                  # Conversation turn number
}
```

## Comparison with Custom Pipeline

| Feature | Bedrock KB | Custom Pipeline |
|---------|------------|-----------------|
| Embeddings | Titan V2 (dense) | OpenAI + BM25 (hybrid) |
| Chunking | ~300 tokens | 1000 chars + 3-tier context |
| Reranking | None | LLM adaptive |
| Page numbers | Not preserved | Preserved |
| Streaming | Not supported | Supported |
| Context | None | Master + Document + Chunk |
| Search | Dense only | RRF fusion (dense + sparse) |

## Testing

```bash
# Handler tests (16 tests)
pytest tests/test_bedrock_kb_handler.py -v

# API integration tests (5 tests)
pytest tests/test_bedrock_kb_integration.py -v

# All Bedrock tests
pytest tests/test_bedrock*.py -v

# Quick evaluation (3 questions)
python -m evaluation.run_evaluation --mode bedrock --test --limit 3
```

### Test Classes

| Class | Tests | Description |
|-------|-------|-------------|
| `TestBedrockKBHandlerInit` | 4 | Handler initialization |
| `TestBedrockKBHandlerQuery` | 3 | Query handling |
| `TestBedrockKBSessionManagement` | 4 | Session tracking |
| `TestBedrockKBErrorHandling` | 1 | Error responses |
| `TestBedrockKBCitations` | 4 | Citation extraction |
| `TestBedrockKBAPI` | 5 | API integration |
| `TestBedrockCitationURLs` | 3 | Full source URL verification |

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `chatbot/handlers/bedrock_kb_handler.py` | ~290 | Main handler class |
| `chatbot/prompts/bedrock_agent_prompt.py` | ~55 | Custom prompt template |
| `evaluation/bedrock_evaluator.py` | ~110 | Evaluation framework evaluator |
| `evaluation/bedrock_model_resolver.py` | 127 | Model name resolution |
| `LOAD_DB/generate_bedrock_metadata.py` | ~160 | Generate .metadata.json files |
| `LOAD_DB/upload_bedrock_metadata.py` | ~180 | Upload to S3 and resync KB |
| `tests/test_bedrock_kb_handler.py` | 246 | Handler unit tests |
| `tests/test_bedrock_kb_integration.py` | ~210 | API and citation URL tests |
| `backend/api/routes.py` | - | API endpoints (bedrock_agent mode) |
| `frontend/components/ModelSettings.tsx` | - | UI settings panel |

## Evaluation Commands

```bash
# Run full evaluation
python -m evaluation.run_evaluation --mode bedrock

# Test mode with limit
python -m evaluation.run_evaluation --mode bedrock --test --limit 5

# With specific model
BEDROCK_MODEL=nova-pro python -m evaluation.run_evaluation --mode bedrock

# Debug mode
python -m evaluation.run_evaluation --mode bedrock --debug --limit 1

# Resume from checkpoint
python -m evaluation.run_evaluation --mode bedrock --resume
```

## Troubleshooting

### No Citations Returned

If `sources` array is empty, verify:
1. Custom prompt includes `$output_format_instructions$` placeholder
2. Knowledge Base has indexed documents
3. Query matches document content

### Model Access Denied

Anthropic models may require use case form submission. Use Amazon Nova models which require no approval:
```bash
BEDROCK_MODEL=nova-micro python -m evaluation.run_evaluation --mode bedrock
```

### Session Not Persisting

Ensure same `thread_id` is passed across requests. Handler caches Bedrock session ID internally.

### AWS MCP Server
Feel free to use AWS MCP Server as necessary