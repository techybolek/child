# Feature: Bedrock Knowledge Base Mode for Chatbot & UI

## Feature Description
Add Amazon Bedrock Knowledge Base as a third mode option in the interactive chatbot CLI and web UI, alongside "RAG Pipeline" and "OpenAI Agent" modes. Users can switch to Bedrock mode via CLI flag (`--provider bedrock`) or UI mode selector. This enables direct comparison of AWS's managed RAG solution (Bedrock KB with Titan embeddings and Nova models) against the custom RAG pipeline (Qdrant + hybrid search + adaptive reranking) and OpenAI Agent mode (GPT models + FileSearchTool).

The feature reuses the existing `BedrockKBEvaluator` implementation and follows the established handler pattern already used for OpenAI and Vertex agents, ensuring consistency across the codebase.

## User Story
As a developer testing RAG approaches
I want to query the Bedrock Knowledge Base directly through the chatbot CLI and web UI
So that I can compare AWS's managed RAG solution against our custom pipeline in a real-time, interactive manner without switching to evaluation mode

## Problem Statement
The application currently supports two runtime modes:
1. **RAG Pipeline** - Custom implementation with Qdrant, hybrid search (dense + BM25), 3-tier contextual embeddings, and adaptive LLM-based reranking
2. **OpenAI Agent** - OpenAI Agents SDK with FileSearchTool for RAG

Amazon Bedrock Knowledge Base is already integrated for evaluation (`bedrock_evaluator.py`) but cannot be used interactively. Users who want to test Bedrock KB responses in real-time must use the evaluation framework, which is designed for batch testing, not interactive exploration.

This creates friction when comparing managed vs custom RAG solutions, as developers cannot easily A/B test responses or iterate on questions in a conversational flow.

## Solution Statement
Implement Bedrock KB as a third chat mode by:

1. **Backend**: Create `BedrockHandler` (adapting `BedrockKBEvaluator`) and route `mode: bedrock_kb` requests through it
2. **CLI**: Add `--provider bedrock` flag and `--bedrock-model` option to `interactive_chat.py`
3. **Frontend**: Add "Bedrock KB" to the mode selector (segmented control) and show model dropdown (Nova Micro/Lite/Pro) in settings panel
4. **API**: Extend `/api/chat` to accept `bedrock_model` parameter and handle `mode: bedrock_kb`

The solution follows the established OpenAI Agent pattern: separate handler, mode-based routing, model selection in UI, and session management.

## Relevant Files

### Backend Files (Python)
- **`evaluation/bedrock_evaluator.py`** - Reference implementation for Bedrock KB queries. Contains the `retrieve_and_generate` API logic, citation extraction, and model ARN resolution. Will be adapted into `BedrockHandler`.

- **`evaluation/bedrock_model_resolver.py`** - Model name resolution utility. Maps short names like `nova-micro` to full ARNs. Handles both foundation models and inference profiles. Will be imported by `BedrockHandler`.

- **`chatbot/handlers/base.py`** - Base handler interface. Defines the `handle()` contract that all handlers must implement. `BedrockHandler` will inherit from `BaseHandler`.

- **`chatbot/handlers/openai_agent_handler.py`** - Reference handler for OpenAI Agent mode. Shows the pattern for async/sync handling, conversation management, and error handling. `BedrockHandler` will follow this pattern.

- **`backend/main.py`** - FastAPI application entry point. Currently routes `mode: openai_agent` and `mode: vertex_agent`. Will add routing for `mode: bedrock_kb`.

- **`backend/api/routes.py`** - API route definitions. Contains `/api/chat` endpoint that handles mode routing (lines 181-357). Will add Bedrock KB routing logic here.

- **`backend/api/models.py`** - Pydantic request/response models. `ChatRequest` model (lines 8-68) will be extended with `bedrock_model` field. Already has `mode` field with `openai_agent` and `vertex_agent` literals.

- **`interactive_chat.py`** - CLI entry point. Currently accepts `--mode` for hybrid/dense/kendra/openai. Will add `--provider bedrock` and `--bedrock-model` flags.

### Frontend Files (TypeScript/React)
- **`frontend/lib/types.ts`** - TypeScript type definitions. `ChatMode` type (line 31) will be extended to include `'bedrock_kb'`. `ChatRequest` interface (lines 47-59) will add `bedrock_model?: string`.

- **`frontend/lib/api.ts`** - API client functions. `askQuestion()` function (lines 22-60) will be extended to accept and pass `bedrockModel` parameter to backend.

- **`frontend/components/ChatInterface.tsx`** - Main chat component. Manages chat mode state (line 38), handles mode switching (lines 94-101), and routes requests based on mode (lines 103-222). Will add Bedrock KB mode handling.

- **`frontend/components/ModelSettings.tsx`** - Settings panel component. Renders mode selector (lines 118-150+) and model dropdowns. Will add Bedrock KB option to mode selector and conditional Bedrock model dropdown.

### Test Files
- **`tests/test_evaluation_e2e_bedrock.py`** - E2E test for Bedrock evaluator. Shows how to check AWS credentials, run Bedrock queries, and validate responses. Will serve as reference for integration tests.

- **`tests/test_openai_agent_api.py`** - API tests for OpenAI Agent mode. Shows pattern for testing mode-specific endpoints: model endpoint, chat endpoint, conversational flow, error handling. Will be duplicated for Bedrock KB tests.

### New Files

- **`chatbot/handlers/bedrock_handler.py`** - New handler for Bedrock KB mode. Adapts `BedrockKBEvaluator` to implement `BaseHandler` interface. Provides both sync `handle()` and async `handle_async()` methods.

- **`backend/api/routes.py` (new endpoint)** - Add `GET /api/models/bedrock-kb` endpoint to return available Nova models (Micro, Lite, Pro) and default.

- **`tests/test_bedrock_handler.py`** - Unit tests for `BedrockHandler`. Tests initialization, query method, error handling, and model resolution.

- **`tests/test_bedrock_agent_api.py`** - API tests for Bedrock KB mode. Tests `/api/models/bedrock-kb` endpoint, `/api/chat` with `mode: bedrock_kb`, and error handling.

## Implementation Plan

### Phase 1: Foundation
Create the shared handler infrastructure that both CLI and web UI will use. This includes the Bedrock handler that wraps the AWS SDK, model resolution utilities, and AWS credential validation.

**Key deliverables:**
- `BedrockHandler` class implementing `BaseHandler` interface
- Model name to ARN resolution (reusing `bedrock_model_resolver.py`)
- AWS credential checking utility
- Unit tests for handler

### Phase 2: Core Implementation
Integrate Bedrock mode into the CLI, backend API, and frontend UI. Each layer will support the new mode while maintaining backward compatibility with existing RAG Pipeline and OpenAI Agent modes.

**Key deliverables:**
- CLI accepts `--provider bedrock` and `--bedrock-model` flags
- Backend `/api/chat` routes `mode: bedrock_kb` requests
- Backend `/api/models/bedrock-kb` endpoint
- Frontend mode selector includes "Bedrock KB" option
- Frontend settings panel shows Bedrock model dropdown

### Phase 3: Integration
Add comprehensive testing at all levels (unit, integration, E2E) and validate that all modes work correctly without regressions. Update documentation and ensure the feature is production-ready.

**Key deliverables:**
- Unit tests for `BedrockHandler`
- API integration tests for Bedrock mode
- E2E CLI tests
- Frontend UI validation
- Documentation updates

## Step by Step Tasks

### Step 1: Create BedrockHandler
- Create `chatbot/handlers/bedrock_handler.py`
- Import `BaseHandler` from `chatbot/handlers/base.py`
- Import `resolve_model_arn` from `evaluation/bedrock_model_resolver.py`
- Implement `__init__()` method that:
  - Accepts optional `kb_id` and `model` parameters
  - Defaults `kb_id` to `os.getenv('BEDROCK_KB_ID', '371M2G58TV')`
  - Defaults `model` to `os.getenv('BEDROCK_MODEL', 'nova-micro')`
  - Resolves model to ARN using `resolve_model_arn()`
  - Initializes `boto3.client('bedrock-agent-runtime')` with region from env
- Implement sync `handle()` method that:
  - Accepts `query: str` and optional `thread_id: str` (ignored, Bedrock doesn't use thread_id)
  - Calls `client.retrieve_and_generate()` with question and model ARN
  - Extracts answer from `response['output']['text']`
  - Extracts sources from `response['citations']`
  - Formats sources as list of dicts with `doc`, `pages` (empty list), `url` (empty string)
  - Returns dict with `answer`, `sources`, `response_type: 'rag'`, `action_items: []`
- Implement async `handle_async()` method that wraps sync `handle()` using `asyncio.to_thread()`
- Add docstrings explaining Bedrock KB limitations (no page numbers, no conversational state)

### Step 2: Create unit tests for BedrockHandler
- Create `tests/test_bedrock_handler.py`
- Add `bedrock_configured()` helper function using `boto3.client('sts').get_caller_identity()`
- Add pytest skip decorator: `pytestmark = pytest.mark.skipif(not bedrock_configured(), reason="AWS credentials not configured")`
- Test handler initialization with default parameters
- Test handler initialization with custom kb_id and model
- Test `handle()` method returns dict with required keys: `answer`, `sources`, `response_type`, `action_items`
- Test sources have correct structure: `doc`, `pages`, `url`
- Test invalid model name raises ValueError
- Test missing AWS credentials raises appropriate error
- Run tests: `pytest tests/test_bedrock_handler.py -v`

### Step 3: Update CLI to support Bedrock mode
- Open `interactive_chat.py`
- Update `parser.add_argument('--mode')` to include `'bedrock'` in choices list
- Add `parser.add_argument('--bedrock-model')` with choices `['nova-micro', 'nova-lite', 'nova-pro']` and default `'nova-micro'`
- Update `get_handler()` function to handle `mode == 'bedrock'`:
  - Import `BedrockHandler` from `chatbot.handlers.bedrock_handler`
  - Return `BedrockHandler(model=bedrock_model)` when mode is bedrock
- Update print statement to show Bedrock model when mode is bedrock
- Test CLI: `python interactive_chat.py --mode bedrock --bedrock-model nova-micro`

### Step 4: Add Bedrock models endpoint to backend
- Open `backend/api/routes.py`
- Add new endpoint after line 178 (after `get_vertex_agent_models`):
  ```python
  @router.get("/models/bedrock-kb")
  async def get_bedrock_kb_models() -> Dict[str, Any]:
      """Get available models for Bedrock KB mode"""
      return {
          "models": [
              {"id": "nova-micro", "name": "Nova Micro (Fast)"},
              {"id": "nova-lite", "name": "Nova Lite (Balanced)"},
              {"id": "nova-pro", "name": "Nova Pro (Quality)"},
          ],
          "default": "nova-micro"
      }
  ```
- Test endpoint: `curl http://localhost:8000/api/models/bedrock-kb`

### Step 5: Update backend API models for Bedrock
- Open `backend/api/models.py`
- Update `ChatRequest.mode` field (line 44) to include `'bedrock_kb'` in Literal type
- Add `bedrock_model` field after `vertex_agent_model` (after line 55):
  ```python
  bedrock_model: Optional[str] = Field(
      None,
      description="Model for Bedrock KB mode (e.g., 'nova-micro', 'nova-lite', 'nova-pro')"
  )
  ```
- Update example in `model_config` to show Bedrock mode usage

### Step 6: Add Bedrock routing to backend chat endpoint
- Open `backend/api/routes.py`
- In `chat()` function, add Bedrock handling after Vertex Agent block (after line 247):
  ```python
  # --- Bedrock KB Mode ---
  elif request.mode == 'bedrock_kb':
      from chatbot.handlers.bedrock_handler import BedrockHandler

      start_time = time.time()

      # No caching needed - Bedrock doesn't have conversational state
      handler = BedrockHandler(model=request.bedrock_model or "nova-micro")

      result = handler.handle(request.question)
      result['processing_time'] = round(time.time() - start_time, 2)
  ```
- Ensure error handling wraps Bedrock handler calls (already in place via try/except block)

### Step 7: Update frontend types for Bedrock
- Open `frontend/lib/types.ts`
- Update `ChatMode` type (line 31) to include `'bedrock_kb'`:
  ```typescript
  export type ChatMode = 'rag_pipeline' | 'openai_agent' | 'vertex_agent' | 'bedrock_kb'
  ```
- Add Bedrock models constant after `VERTEX_AGENT_MODELS` (after line 45):
  ```typescript
  export const BEDROCK_KB_MODELS = [
    { id: 'nova-micro', name: 'Nova Micro (Fast)' },
    { id: 'nova-lite', name: 'Nova Lite (Balanced)' },
    { id: 'nova-pro', name: 'Nova Pro (Quality)' },
  ] as const
  ```
- Add `bedrock_model?: string` field to `ChatRequest` interface (after line 58)

### Step 8: Update frontend API client for Bedrock
- Open `frontend/lib/api.ts`
- Add `bedrockModel?: string` parameter to `askQuestion()` function signature (after line 35)
- Add `bedrock_model: bedrockModel` to request body (after line 49)
- Add `fetchBedrockKbModels()` function after `fetchVertexAgentModels()` (after line 117):
  ```typescript
  export async function fetchBedrockKbModels(): Promise<{ models: { id: string; name: string }[]; default: string }> {
    const response = await fetch(`${API_BASE_URL}/api/models/bedrock-kb`)
    if (!response.ok) {
      throw new Error('Failed to fetch Bedrock KB models')
    }
    return response.json()
  }
  ```

### Step 9: Update ChatInterface component for Bedrock
- Open `frontend/components/ChatInterface.tsx`
- Import `BEDROCK_KB_MODELS` from `@/lib/types` (line 9)
- Add `bedrockKbModel` state after `vertexAgentModel` (after line 40):
  ```typescript
  const [bedrockKbModel, setBedrockKbModel] = useState<string>(BEDROCK_KB_MODELS[0].id) // nova-micro default
  ```
- Update `handleSubmit()` to pass Bedrock model to `askQuestion()` (around line 197):
  ```typescript
  chatMode === 'bedrock_kb' ? bedrockKbModel : undefined
  ```
- Pass Bedrock props to `ModelSettings` component (around line 272):
  ```typescript
  bedrockKbModel={bedrockKbModel}
  onBedrockKbModelChange={setBedrockKbModel}
  ```

### Step 10: Update ModelSettings component for Bedrock
- Open `frontend/components/ModelSettings.tsx`
- Import `BEDROCK_KB_MODELS` from `@/lib/types` (line 9)
- Add `bedrockKbModel` and `onBedrockKbModelChange` props to interface (after line 41)
- Add fourth button to mode selector (after line 149):
  ```typescript
  <button
    onClick={() => onChatModeChange('bedrock_kb')}
    className={`flex-1 px-2 py-2 text-xs rounded-r-md ${
      chatMode === 'bedrock_kb'
        ? 'bg-blue-600 text-white'
        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
    }`}
    title="Amazon Bedrock Knowledge Base with Nova models"
  >
    Bedrock KB
  </button>
  ```
- Add Bedrock model dropdown in conditional section (search for `chatMode === 'vertex_agent'` and add similar block):
  ```typescript
  {chatMode === 'bedrock_kb' && (
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-700">
        Bedrock Model
      </label>
      <select
        value={bedrockKbModel}
        onChange={(e) => onBedrockKbModelChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
      >
        {BEDROCK_KB_MODELS.map((model) => (
          <option key={model.id} value={model.id}>
            {model.name}
          </option>
        ))}
      </select>
    </div>
  )}
  ```

### Step 11: Create API integration tests for Bedrock
- Create `tests/test_bedrock_agent_api.py`
- Copy structure from `tests/test_openai_agent_api.py`
- Update module docstring to reference Bedrock KB mode
- Add `bedrock_configured()` helper using `boto3.client('sts').get_caller_identity()`
- Add pytest skip decorator for missing AWS credentials
- Create `TestBedrockKBModelsEndpoint` class:
  - Test endpoint returns 200 with models list and default
  - Test returns expected models (nova-micro, nova-lite, nova-pro)
  - Test each model has id and name fields
- Create `TestBedrockKBChatEndpoint` class:
  - Test returns answer, sources, session_id, timestamp, processing_time
  - Test answer is non-empty (> 10 chars)
  - Test sources have correct structure
- Create `TestBedrockKBErrorHandling` class:
  - Test invalid mode returns 422
  - Test empty question returns 422
  - Test invalid model name handled gracefully
- Run tests: `pytest tests/test_bedrock_agent_api.py -v`

### Step 12: Run validation commands
- Start backend: `cd backend && python main.py`
- Verify backend starts without errors
- Verify `/api/models/bedrock-kb` endpoint returns Nova models
- Test CLI with Bedrock mode: `python interactive_chat.py --mode bedrock --bedrock-model nova-micro`
- Ask test question: "What is CCS?"
- Verify response includes answer and sources
- Test frontend build: `cd frontend && npm run build`
- Verify build succeeds without errors
- Run all Bedrock tests: `pytest tests/test_bedrock_handler.py tests/test_bedrock_agent_api.py -v`
- Run regression test for hybrid mode: `python -m evaluation.run_evaluation --mode hybrid --test --limit 3`
- Run quick Bedrock evaluation: `python -m evaluation.run_evaluation --mode bedrock --test --limit 3`

## Testing Strategy

### Unit Tests
- **BedrockHandler class** (`tests/test_bedrock_handler.py`)
  - Initialization with default and custom parameters
  - Model ARN resolution (nova-micro, nova-lite, nova-pro)
  - Sync `handle()` method returns correct response structure
  - Async `handle_async()` method works correctly
  - Error handling for invalid models
  - Error handling for missing AWS credentials
  - Source extraction and formatting

### Integration Tests
- **Backend API** (`tests/test_bedrock_agent_api.py`)
  - GET `/api/models/bedrock-kb` returns Nova models
  - POST `/api/chat` with `mode: bedrock_kb` and `bedrock_model: nova-micro`
  - Response includes answer, sources, metadata
  - Invalid mode value returns 422
  - Empty question returns 422
  - Invalid model name handled gracefully

- **CLI** (manual testing)
  - `python interactive_chat.py --mode bedrock` uses default nova-micro model
  - `python interactive_chat.py --mode bedrock --bedrock-model nova-pro` uses specified model
  - Question/answer flow works correctly
  - Sources are displayed
  - Error handling for missing credentials

- **Frontend** (manual testing in browser)
  - Mode selector shows "Bedrock KB" option
  - Clicking "Bedrock KB" clears chat and switches mode
  - Settings panel shows Bedrock model dropdown (Nova Micro, Lite, Pro)
  - Changing model updates request to backend
  - Question/answer flow works correctly
  - Sources are displayed
  - Error messages shown for API failures

### Edge Cases
- **AWS credentials not configured**: Should show clear error message, not crash
- **Invalid Bedrock model name**: Should fallback to nova-micro or show error
- **Bedrock KB not available**: Should return error response with retry suggestion
- **Network timeout**: Should handle gracefully with timeout error
- **Switch mode mid-conversation**: Should clear chat history and start fresh session
- **Empty question**: Should return 422 validation error
- **Rate limit exceeded**: Should show error with retry suggestion
- **Missing BEDROCK_KB_ID env var**: Should use default `371M2G58TV`
- **Invalid KB ID**: Should return AWS API error with clear message

## Acceptance Criteria
- [ ] CLI accepts `--mode bedrock` flag and uses Bedrock KB handler
- [ ] CLI accepts `--bedrock-model` flag with values: nova-micro, nova-lite, nova-pro
- [ ] Environment variable `BEDROCK_MODEL` sets default model (default: nova-micro)
- [ ] Backend `/api/models/bedrock-kb` endpoint returns Nova models list
- [ ] Backend `/api/chat` with `mode: bedrock_kb` routes to BedrockHandler
- [ ] UI mode selector shows four options: RAG Pipeline, OpenAI Agent, Vertex Agent, Bedrock KB
- [ ] Bedrock KB mode shows model dropdown with Nova Micro, Lite, Pro options
- [ ] Switching to Bedrock KB mode clears chat history
- [ ] Bedrock responses include answer text and source citations (when available)
- [ ] RAG Pipeline mode remains default on page load and CLI invocation
- [ ] Mode selection does NOT persist across page refresh (always resets to RAG Pipeline)
- [ ] All unit tests pass: `pytest tests/test_bedrock_handler.py -v`
- [ ] All API tests pass: `pytest tests/test_bedrock_agent_api.py -v`
- [ ] Regression test passes: `python -m evaluation.run_evaluation --mode hybrid --test --limit 3`
- [ ] Bedrock evaluation works: `python -m evaluation.run_evaluation --mode bedrock --test --limit 3`
- [ ] Frontend builds without errors: `cd frontend && npm run build`
- [ ] Backend starts without errors: `cd backend && python main.py`

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# Backend validation
cd backend && python main.py &
sleep 5
curl http://localhost:8000/api/health | jq
curl http://localhost:8000/api/models/bedrock-kb | jq
kill %1

# Unit tests
pytest tests/test_bedrock_handler.py -v

# API integration tests
pytest tests/test_bedrock_agent_api.py -v

# CLI validation (interactive - manual test)
python interactive_chat.py --mode bedrock --bedrock-model nova-micro
# Ask: "What is CCS?"
# Verify response and sources

# Frontend build
cd frontend && npm run build

# Regression tests (ensure no breakage)
python -m evaluation.run_evaluation --mode hybrid --test --limit 3
python -m evaluation.run_evaluation --mode bedrock --test --limit 3

# E2E test for Bedrock evaluator (should still work)
pytest tests/test_evaluation_e2e_bedrock.py -v
```

## Notes

### AWS Configuration Requirements
Users must have AWS credentials configured with Bedrock access:
- `AWS_REGION` environment variable (default: us-east-1)
- `BEDROCK_KB_ID` environment variable (default: 371M2G58TV)
- AWS credentials via environment variables, IAM role, or `~/.aws/credentials`
- IAM permissions: `bedrock:InvokeModel`, `bedrock:Retrieve`, `bedrock-agent-runtime:RetrieveAndGenerate`

### Model Availability
**Amazon Nova models (no approval required):**
- `nova-micro` - Fast, cost-effective (default)
- `nova-lite` - Balanced performance and cost
- `nova-pro` - Highest quality, slower

**Anthropic Claude models (may require use case form):**
- Not included in initial implementation to avoid approval delays
- Can be added later via `bedrock_model_resolver.py` once approved

### Bedrock KB Limitations (vs Custom RAG Pipeline)
- **No page numbers**: Bedrock KB doesn't preserve PDF page metadata
- **Default chunking**: ~300 tokens (vs custom 1000 chars with overlap)
- **Dense-only search**: No hybrid search (vs RRF fusion with BM25)
- **No reranking**: No adaptive chunk selection (vs LLM-based reranking)
- **No contextual embeddings**: No 3-tier context enhancement
- **No conversational state**: Each query is independent (vs custom conversation memory)

### Development Dependencies
No new Python packages required - `boto3` already in `requirements.txt` for Bedrock evaluation.

### Future Enhancements (Out of Scope)
- Streaming responses for Bedrock mode (not supported by retrieve_and_generate API)
- Conversational state (Bedrock KB is stateless)
- Custom KB configuration (currently hardcoded to 371M2G58TV)
- Claude models on Bedrock (requires AWS approval)
- Kendra mode in UI (evaluation-only, not a runtime mode)
- Persisting mode preference (always defaults to RAG Pipeline)

### Implementation Reference
This feature follows the exact same pattern as OpenAI Agent and Vertex Agent modes:
1. Handler class implementing `BaseHandler` interface
2. Mode-based routing in backend `/api/chat` endpoint
3. Model selection endpoint (`/api/models/bedrock-kb`)
4. UI mode selector with fourth button
5. Conditional settings panel based on mode
6. Session management (though Bedrock doesn't use it)
7. Integration tests mirroring OpenAI Agent tests

### Testing Notes
- All Bedrock tests skip if AWS credentials not configured (using `pytest.mark.skipif`)
- Manual CLI testing requires AWS credentials and Knowledge Base synced
- Frontend testing requires backend running with AWS credentials
- Use `--test --limit 3` for quick validation during development
