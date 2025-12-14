# Feature Request: Bedrock Knowledge Base Mode for Chatbot & UI

**Date:** 2025-12-14
**Status:** Refined

## Overview
Add Amazon Bedrock Knowledge Base as a third mode option in the interactive chatbot CLI and web UI, alongside "RAG Pipeline" and "OpenAI Agent". Users can switch to Bedrock mode via environment variable, CLI flag, or UI settings panel.

## Problem Statement
The application already supports OpenAI Agent mode as an alternative to the custom RAG pipeline. Bedrock Knowledge Base is integrated for evaluation (`bedrock_evaluator.py`) but not available as a runtime option. Adding Bedrock mode enables comparison of AWS's managed RAG solution against the custom pipeline and OpenAI Agent.

## Users & Stakeholders
- Primary Users: Developers testing/comparing RAG approaches
- Secondary: Anyone wanting to use AWS Bedrock as their retrieval backend

## Functional Requirements

1. **CLI Support**: `python interactive_chat.py --provider bedrock`
2. **Environment Variable**: `LLM_PROVIDER=bedrock` enables Bedrock mode
3. **UI Mode Selector**: Third option "Bedrock KB" in mode selector
4. **Model Selection**: Dropdown for Nova Micro/Lite/Pro models
5. **Default Behavior**: RAG Pipeline remains default (Bedrock is opt-in)
6. **Follow Existing Pattern**: Same UX as OpenAI Agent mode switching

## User Flow

### CLI
1. User runs `python interactive_chat.py --provider bedrock`
2. Optionally specify model: `--bedrock-model nova-pro`
3. Chat uses Bedrock KB `retrieve_and_generate` API

### UI
1. User loads chat UI → RAG Pipeline mode active by default
2. User clicks mode selector, sees three options: "RAG Pipeline", "OpenAI Agent", "Bedrock KB"
3. User selects "Bedrock KB"
4. Chat clears, settings panel shows Bedrock model dropdown
5. User selects model (default: Nova Micro) and starts conversation

## Acceptance Criteria

- [ ] CLI accepts `--provider bedrock` flag
- [ ] CLI accepts `--bedrock-model` flag (nova-micro, nova-lite, nova-pro)
- [ ] Environment variable `LLM_PROVIDER=bedrock` activates Bedrock mode
- [ ] Environment variable `BEDROCK_MODEL` sets model (default: nova-micro)
- [ ] UI mode selector shows three options: "RAG Pipeline", "OpenAI Agent", "Bedrock KB"
- [ ] Bedrock KB mode shows model dropdown with: Nova Micro, Nova Lite, Nova Pro
- [ ] Switching to Bedrock KB mode clears chat history
- [ ] Bedrock responses include citations when available
- [ ] RAG Pipeline remains default on page load
- [ ] Mode selection does NOT persist across page refresh

## User Experience

- **Interface**: CLI (`interactive_chat.py`) + Web UI
- **Key Interactions**:
  - CLI: `--provider bedrock --bedrock-model nova-pro`
  - UI: Mode selector as segmented control with three options
  - Settings panel updates contextually based on mode
- **Feedback**:
  - Chat clears visibly when switching modes
  - Error message if AWS credentials invalid or KB unavailable

## Technical Requirements

### CLI Changes

**Modified Files:**
- `interactive_chat.py` - Add `--provider` and `--bedrock-model` arguments

**New Handler:**
- Reuse/adapt `BedrockKBEvaluator` from `evaluation/bedrock_evaluator.py`

### Frontend Changes

**Modified Files:**
- `frontend/lib/types.ts` - Add 'bedrock_kb' mode, Bedrock model list
- `frontend/lib/api.ts` - Update request to include Bedrock params
- `frontend/components/ChatInterface.tsx` - Add Bedrock to mode state
- `frontend/components/ModelSettings.tsx` - Conditional rendering for Bedrock

**State:**
```typescript
type ChatMode = 'rag_pipeline' | 'openai_agent' | 'bedrock_kb';

const BEDROCK_MODELS = [
  { value: 'nova-micro', label: 'Nova Micro (Fast)' },
  { value: 'nova-lite', label: 'Nova Lite (Balanced)' },
  { value: 'nova-pro', label: 'Nova Pro (Quality)' }
];
```

### Backend Changes

**Modified Files:**
- `backend/main.py` - Handle `mode: bedrock_kb`, route to Bedrock handler

**New Files:**
- `chatbot/handlers/bedrock_handler.py` - Bedrock KB handler (adapt from evaluator)

**Request Schema Update:**
```json
{
  "question": "...",
  "session_id": "...",
  "mode": "rag_pipeline" | "openai_agent" | "bedrock_kb",
  // Bedrock KB params (ignored if mode != bedrock_kb)
  "bedrock_model": "nova-micro"
}
```

### AWS Configuration

**Required Environment Variables:**
- `AWS_REGION` - Default: us-east-1
- `BEDROCK_KB_ID` - Knowledge Base ID (371M2G58TV)
- AWS credentials (via environment, IAM role, or credentials file)

**Bedrock Model ARN Mapping:**
```python
BEDROCK_MODELS = {
    'nova-micro': 'amazon.nova-micro-v1:0',
    'nova-lite': 'amazon.nova-lite-v1:0',
    'nova-pro': 'amazon.nova-pro-v1:0',
}
```

### Performance
- Mode switching instant (client-side state change)
- Bedrock API latency varies by model (Micro fastest, Pro slowest)

### Security
- AWS credentials configured server-side
- No credentials exposed to frontend

## Data Model

- **Storage**: No new persistent storage
- **Session**: Bedrock KB handles session internally
- **Retention**: N/A (no persistence)

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| AWS credentials missing | Show error: "AWS credentials not configured" |
| Knowledge Base unavailable | Show error: "Bedrock Knowledge Base unavailable" |
| Invalid model selection | Fallback to nova-micro |
| Rate limit exceeded | Show error with retry suggestion |
| Switch mode mid-typing | Clear input along with chat history |

## Dependencies

- **Requires**:
  - AWS credentials with Bedrock access
  - Bedrock Knowledge Base (371M2G58TV) synced with PDFs
  - `bedrock_evaluator.py` as reference implementation
- **Blocks**: Nothing

## Out of Scope

- Claude models on Bedrock (require AWS use case approval)
- Streaming responses for Bedrock mode
- Persisting mode preference
- Custom Bedrock KB configuration (ID is fixed)
- Kendra mode in UI (evaluation-only)

## Success Metrics

- Users can successfully switch to Bedrock mode via CLI and UI
- Bedrock responses return correctly with citations
- No regression in RAG Pipeline or OpenAI Agent functionality

## Implementation Notes

### UI Layout

```
┌─────────────────────────────────────────────────────┐
│  [RAG Pipeline]  [OpenAI Agent]  [Bedrock KB]       │  ← Segmented control
├─────────────────────────────────────────────────────┤
│  Settings (contextual)                              │
│  ┌───────────────────────────────────────────┐      │
│  │ Bedrock Model: [Nova Micro (Fast)    ▼]   │      │  ← Bedrock: single dropdown
│  └───────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

### CLI Usage

```bash
# Default (RAG Pipeline)
python interactive_chat.py

# Bedrock mode with default model
python interactive_chat.py --provider bedrock

# Bedrock mode with specific model
python interactive_chat.py --provider bedrock --bedrock-model nova-pro

# Via environment variable
BEDROCK_MODEL=nova-lite python interactive_chat.py --provider bedrock
```

### Backend Routing Logic

```python
# backend/main.py
if request.mode == "bedrock_kb":
    response = bedrock_handler.ask(
        question=request.question,
        model=request.bedrock_model or "nova-micro"
    )
elif request.mode == "openai_agent":
    response = openai_agent_handler.ask(...)
else:
    response = chatbot.ask(...)  # RAG Pipeline
```

### Handler Implementation Reference

Adapt from `evaluation/bedrock_evaluator.py`:

```python
# chatbot/handlers/bedrock_handler.py
class BedrockHandler:
    def __init__(self, kb_id: str = "371M2G58TV", model: str = "nova-micro"):
        self.client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        self.kb_id = kb_id
        self.model_arn = BEDROCK_MODELS[model]

    def ask(self, question: str, model: str = None) -> dict:
        response = self.client.retrieve_and_generate(
            input={'text': question},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': f'arn:aws:bedrock:us-east-1::foundation-model/{self.model_arn}'
                }
            }
        )
        return {
            'answer': response['output']['text'],
            'citations': self._extract_citations(response)
        }
```
