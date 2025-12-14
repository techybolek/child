# Feature: Bedrock Knowledge Base Integration

## Feature Description
Add Amazon Bedrock Knowledge Base as a new chat mode in the chatbot UI and backend, enabling users to compare AWS managed RAG (Bedrock KB) against the custom RAG pipeline, OpenAI Agent, and Vertex Agent modes. This feature provides a fourth chat mode button in the UI that routes queries through AWS Bedrock's retrieve_and_generate API using an existing pre-configured Knowledge Base (ID: 371M2G58TV) with Amazon Nova models.

The feature allows users to test and compare managed AWS RAG performance directly in the chat interface, supporting the evaluation workflow and providing insights into different RAG approaches.

## User Story
As a developer or evaluator testing different RAG approaches
I want to select "Bedrock Agent" mode in the chatbot UI
So that I can compare AWS managed RAG performance against custom pipeline, OpenAI Agent, and Vertex Agent modes in real-time

## Problem Statement
The evaluation system already supports Bedrock KB for batch testing (`bedrock` mode in `run_evaluation.py`), but the chatbot UI and interactive interface don't expose this capability to users. This creates a gap between evaluation capabilities and real-time testing. Users need to compare managed AWS RAG (Bedrock KB) against the custom RAG pipeline and other agent modes directly in the chat interface to understand performance differences, make informed architectural decisions, and validate evaluation results interactively.

Without UI integration, users must rely solely on batch evaluation results and cannot iteratively test and refine Bedrock KB configurations.

## Solution Statement
Extend the existing handler pattern (similar to OpenAI Agent and Vertex Agent) to add Bedrock KB support to both backend and frontend. Create a new `BedrockKBHandler` that wraps AWS Bedrock's `retrieve_and_generate` API, add backend routing in FastAPI, expose a new "Bedrock Agent" button in the chat mode selector, and provide model selection for the 3 Amazon Nova models (nova-micro, nova-lite, nova-pro).

The solution reuses existing evaluation code (`BedrockKBEvaluator`) as reference, follows the established agent handler pattern, and maintains conversation continuity using Bedrock's session management - all with minimal code duplication and maximum consistency with existing architecture.

## Relevant Files

### Backend Handler
- **chatbot/handlers/bedrock_kb_handler.py** (NEW) - Main handler class implementing BaseHandler interface, wraps AWS Bedrock retrieve_and_generate API, manages conversation sessions, parses citations into sources format
  - Pattern: Similar to `openai_agent_handler.py` and `vertex_agent_handler.py`
  - Reference: `evaluation/bedrock_evaluator.py` for Bedrock API calls

- **chatbot/handlers/base.py** - Base handler interface that BedrockKBHandler will implement (defines `handle()` and `handle_async()` methods)

### Backend API
- **backend/api/routes.py** - Add routing for `mode='bedrock_agent'` in `/api/chat` endpoint, add `/api/models/bedrock-agent` endpoint for model list, add handler caching per session in `_conversational_chatbots`
  - Lines 210-247: OpenAI Agent routing pattern to follow
  - Lines 141-159: OpenAI Agent models endpoint pattern to follow

- **backend/api/models.py** - Add `bedrock_agent` to `ChatMode` type, add `bedrock_agent_model` field to `ChatRequest` model
  - Line 44: Update `ChatMode` Literal to include 'bedrock_agent'
  - Line 51-55: Add `bedrock_agent_model` field similar to `openai_agent_model` and `vertex_agent_model`

### Configuration
- **chatbot/config.py** - Add Bedrock KB configuration: `BEDROCK_KB_ID`, `BEDROCK_AGENT_MODEL`, `AWS_REGION`
  - Lines 87-96: Existing OpenAI/Vertex agent config pattern to follow

### Prompts
- **chatbot/prompts/bedrock_agent_prompt.py** (NEW) - System prompt for Bedrock agent, optimized for Amazon Nova models with critical domain rules
  - Reference: `vertex_agent_prompt.py` (clean structure) and `response_generation_prompt.py` (domain-specific rules)
  - ~40-50 lines balancing Nova model capabilities with Texas childcare domain requirements

- **chatbot/prompts/__init__.py** - Export bedrock agent prompt constant

### Frontend Types
- **frontend/lib/types.ts** - Add `bedrock_agent` to `ChatMode` type, add `BEDROCK_AGENT_MODELS` constant, add `bedrock_agent_model` to `ChatRequest` interface
  - Line 31: Update ChatMode type
  - Lines 33-45: Add BEDROCK_AGENT_MODELS constant similar to OPENAI_AGENT_MODELS and VERTEX_AGENT_MODELS
  - Lines 47-59: Add bedrock_agent_model field to ChatRequest

### Frontend Components
- **frontend/components/ChatInterface.tsx** - Add `bedrockAgentModel` state, handle Bedrock mode in submit logic
  - Line 38-40: Add bedrockAgentModel state similar to openaiAgentModel and vertexAgentModel
  - Lines 122-130: Add Bedrock mode to submit handler

- **frontend/components/ModelSettings.tsx** - Add "Bedrock Agent" button to chat mode selector (4 buttons total), add Bedrock settings section with model dropdown and info box
  - Lines 118-165: Chat mode selector - add 4th button for Bedrock Agent
  - Lines 167-192: Add Bedrock Agent settings section similar to OpenAI/Vertex sections

### Frontend API
- **frontend/lib/api.ts** - Pass `bedrock_agent_model` to backend in chat requests (likely already generic enough to handle)

### Tests (New Files)
- **tests/test_bedrock_kb_handler.py** (NEW) - Integration tests for BedrockKBHandler using real AWS Bedrock KB (no mocking)
- **tests/test_bedrock_kb_integration.py** (NEW) - End-to-end API integration tests using FastAPI TestClient with real Bedrock calls
- **tests/test_bedrock_kb_ui.py** (NEW) - Frontend type/component tests if applicable (optional)

### Reference Files
- **evaluation/bedrock_evaluator.py** - Reference for Bedrock KB API calls, model resolution, citation parsing
- **evaluation/bedrock_model_resolver.py** - Reference for model name to ARN resolution (can reuse or simplify)

## Implementation Plan

### Phase 1: Foundation
Set up configuration, create base handler structure, and establish Bedrock KB connectivity. This phase ensures AWS credentials work, the KB is accessible, and basic API calls succeed before building the full handler.

Key tasks:
- Add configuration constants to `chatbot/config.py`
- Create `BedrockKBHandler` class skeleton implementing `BaseHandler`
- Test Bedrock KB connectivity with simple query
- Create optimized system prompt for Amazon Nova models

### Phase 2: Core Implementation
Build the complete handler with conversation management, implement backend API routing, and add comprehensive error handling. This phase creates the full backend functionality needed to support Bedrock mode.

Key tasks:
- Implement `handle()` and `handle_async()` methods in handler
- Add session management for conversation continuity
- Parse Bedrock citations into sources format
- Add backend routing in `/api/chat` endpoint
- Create `/api/models/bedrock-agent` endpoint
- Add handler caching per session

### Phase 3: Integration
Integrate Bedrock mode into the frontend UI, add type definitions, implement model selection, and create end-to-end tests. This phase makes the feature accessible to users and validates the entire flow.

Key tasks:
- Update TypeScript types for Bedrock mode
- Add "Bedrock Agent" button to chat mode selector
- Implement Bedrock settings section in UI
- Add model dropdown and info box
- Create comprehensive test suite
- Validate with manual testing across all 3 models

## Step by Step Tasks

### 1. Add Bedrock KB Configuration
- Add `BEDROCK_KB_ID` to `chatbot/config.py` with default `'371M2G58TV'`
- Add `BEDROCK_AGENT_MODEL` to `chatbot/config.py` with default `'nova-micro'`
- Add `AWS_REGION` to `chatbot/config.py` with default `'us-east-1'`
- Add environment variable documentation in README or .env.example

### 2. Create Bedrock Agent System Prompt
- Create `chatbot/prompts/bedrock_agent_prompt.py`
- Implement 40-50 line prompt following "Vertex+ Model" strategy:
  - Role definition (Texas childcare expert)
  - Core behavioral rules (use only retrieved info, be concise, think before answering)
  - Domain context (TWC, CCS, PSOC, TRS, key organizations)
  - Critical domain rules (income limits with BCY, table year columns, outcomes completeness, abbreviations)
  - Response style guidance (match length to complexity, yes/no first for simple questions)
  - Output format (ANSWER:/SOURCES: structure)
- Export `BEDROCK_AGENT_PROMPT` constant in `chatbot/prompts/__init__.py`
- Test prompt with sample queries to validate output format

### 3. Create BedrockKBHandler Class
- Create `chatbot/handlers/bedrock_kb_handler.py`
- Implement `__init__()` method:
  - Initialize boto3 `bedrock-agent-runtime` client
  - Load configuration from `config.py` (KB_ID, model, region)
  - Resolve model name to ARN (reuse or simplify `bedrock_model_resolver.py`)
  - Initialize session storage dict (`_sessions`)
- Implement `_parse_response()` method:
  - Parse ANSWER:/SOURCES: sections from output
  - Extract answer text
  - Extract sources list from citations
  - Return tuple of (answer, sources)
- Implement conversation management helpers:
  - `new_conversation()` - Generate new session ID
  - `get_history()` - Return conversation history (may be empty for Bedrock sessions)
  - `clear_conversation()` - Clear session from storage

### 4. Implement Handler Query Methods
- Implement `_query_bedrock()` helper method:
  - Accept query and optional session_id
  - Generate session_id if not provided
  - Build `retrieve_and_generate` API request with KB ID, model ARN, and query
  - Include `sessionId` in request for conversation continuity
  - Call Bedrock API and return response
  - Track session in `_sessions` dict
  - Return dict with output_text, session_id, turn_count
- Implement `handle()` sync method:
  - Call `_query_bedrock()`
  - Parse response with `_parse_response()`
  - Build response dict with answer, sources, response_type, action_items, thread_id, turn_count
  - Add debug_info if debug=True
  - Wrap in try/except with error fallback message
- Implement `handle_async()` async method:
  - Same logic as `handle()` but async
  - Use `asyncio.to_thread()` if Bedrock SDK is sync-only
  - Return same response structure

### 5. Add Backend API Type Definitions
- Update `backend/api/models.py`:
  - Add `'bedrock_agent'` to `ChatMode` Literal type (line 44)
  - Add `bedrock_agent_model: Optional[str]` field to `ChatRequest` class (after line 55)
  - Add example in model_config showing bedrock_agent usage

### 6. Add Backend API Routing
- Update `backend/api/routes.py`:
  - Import `BedrockKBHandler` at top of file
  - Add Bedrock Agent mode handling in `/api/chat` endpoint (around line 247):
    - Check `if request.mode == 'bedrock_agent':`
    - Create cache key `f"bedrock_{session_id}"`
    - Get or create handler from `_conversational_chatbots`
    - Call `await handler.handle_async(request.question, thread_id=session_id)`
    - Add processing_time to result
  - Create `/api/models/bedrock-agent` endpoint (around line 179):
    - Return dict with `models` list (3 Amazon Nova models with id and name)
    - Return `default` model from `chatbot_config.BEDROCK_AGENT_MODEL`
    - Follow pattern from `/api/models/openai-agent` and `/api/models/vertex-agent`

### 7. Update Frontend Type Definitions
- Update `frontend/lib/types.ts`:
  - Add `'bedrock_agent'` to `ChatMode` type (line 31)
  - Add `BEDROCK_AGENT_MODELS` constant (after line 45):
    ```typescript
    export const BEDROCK_AGENT_MODELS = [
      { id: 'nova-micro', name: 'Nova Micro' },
      { id: 'nova-lite', name: 'Nova Lite' },
      { id: 'nova-pro', name: 'Nova Pro' },
    ] as const
    ```
  - Add `bedrock_agent_model?: string` to `ChatRequest` interface (line 59)

### 8. Add Bedrock Mode to ChatInterface
- Update `frontend/components/ChatInterface.tsx`:
  - Import `BEDROCK_AGENT_MODELS` from types (line 9)
  - Add `bedrockAgentModel` state with default `BEDROCK_AGENT_MODELS[0].id` (around line 40)
  - Add `setBedrockAgentModel` state setter
  - Pass `bedrockAgentModel` and `setBedrockAgentModel` to `ModelSettings` component
  - Update submit handler to include Bedrock mode (around line 122):
    - Add bedrock to conditions that disable streaming
    - Include `bedrock_agent_model: bedrockAgentModel` in request if mode is `bedrock_agent`

### 9. Add Bedrock UI to ModelSettings Component
- Update `frontend/components/ModelSettings.tsx`:
  - Add `bedrockAgentModel` and `onBedrockAgentModelChange` to props interface (around line 42)
  - Add 4th button to Chat Mode selector (around line 156):
    ```tsx
    <button
      onClick={() => onChatModeChange('bedrock_agent')}
      className={`flex-1 px-2 py-2 text-xs rounded-r-md ${
        chatMode === 'bedrock_agent'
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
      title="Amazon Bedrock KB with Nova models"
    >
      Bedrock Agent
    </button>
    ```
  - Add Bedrock Agent settings section (after Vertex section around line 220):
    - Model dropdown with 3 Amazon Nova models
    - Orange info box: "Bedrock Agent mode is always conversational and uses AWS managed RAG with Amazon Bedrock Knowledge Base."
  - Update mode description text to include Bedrock (around line 159-164)

### 10. Create Integration Tests for BedrockKBHandler
- Create `tests/test_bedrock_kb_handler.py`
- Test handler initialization:
  - Test with default config values from `chatbot/config.py`
  - Test model ARN resolution for all 3 Amazon Nova models
  - Test handler creates boto3 client successfully
- Test query handling with real Bedrock KB calls:
  - Send real query: "What is TWC?"
  - Verify response contains answer text
  - Verify response contains sources with correct structure (doc, pages, url)
  - Verify response parsing extracts answer and sources correctly
- Test session management:
  - Test new_conversation() generates unique UUIDs
  - Send multiple queries with same session_id - verify session tracking
  - Send queries with different session_ids - verify isolation
  - Test clear_conversation() removes session from storage
- Test response parsing:
  - Parse ANSWER:/SOURCES: format from real Bedrock responses
  - Test edge cases (missing sections, extra whitespace)

### 11. Create API Integration Tests
- Create `tests/test_bedrock_kb_integration.py`
- Test end-to-end flow using FastAPI TestClient:
  - Use TestClient (no need to start server)
  - Send POST to `/api/chat` with `mode='bedrock_agent'`
  - Verify response structure (answer, sources, session_id, timestamp, processing_time)
  - Verify handler caching works across requests with same session_id
- Test model endpoint:
  - Send GET to `/api/models/bedrock-agent`
  - Verify 3 models returned (nova-micro, nova-lite, nova-pro)
  - Verify default model matches config value
- Test conversation flow:
  - Send multiple queries with same session_id
  - Verify conversation isolation between different session_ids

### 12. Manual Testing and Validation
- Test UI mode switching:
  - Switch between all 4 modes (RAG Pipeline, OpenAI Agent, Vertex Agent, Bedrock Agent)
  - Verify settings panel updates correctly
  - Verify conversation clears on mode switch
- Test Bedrock Agent mode:
  - Send simple query (e.g., "What is TWC?")
  - Verify answer displays correctly
  - Verify sources appear in source cards
  - Verify no streaming toggle shown
  - Verify no conversational toggle shown
- Test all 3 models:
  - Select nova-micro, send query
  - Select nova-lite, send query
  - Select nova-pro, send query
  - Verify all work without errors
- Test conversation continuity:
  - Ask follow-up question referencing previous answer
  - Verify context maintained (if supported)
- Test error handling:
  - Send query with invalid credentials (if testable)
  - Verify error message displays properly

### 13. Run Validation Commands
- Execute all validation commands to ensure zero regressions
- Fix any issues found
- Verify all tests pass
- Verify UI builds and runs without errors

## Testing Strategy

**Philosophy:** All tests use real AWS Bedrock KB integration - no mocking. AWS credentials already configured (same setup as existing `bedrock_evaluator.py`).

### Integration Tests
**File:** `tests/test_bedrock_kb_handler.py`

- **Handler Initialization:**
  - Test default config values load correctly from `chatbot/config.py`
  - Test model ARN resolution for all 3 Amazon Nova models (nova-micro, nova-lite, nova-pro)
  - Test handler creates boto3 client successfully

- **Query Handling (Real Bedrock Calls):**
  - Send real query to Bedrock KB: "What is TWC?"
  - Verify response contains answer text
  - Verify response contains sources list with correct structure
  - Test response parsing extracts answer correctly
  - Test response parsing extracts sources correctly

- **Session Management:**
  - Test `new_conversation()` generates unique UUIDs
  - Send multiple queries with same session_id - verify session tracking
  - Send queries with different session_ids - verify isolation
  - Test `clear_conversation()` removes session from storage

- **Response Parsing:**
  - Parse ANSWER:/SOURCES: format from real Bedrock responses
  - Test handling of various source formats
  - Test edge cases (missing sections, extra whitespace)

**File:** `tests/test_bedrock_kb_integration.py`

- **End-to-End API (FastAPI TestClient):**
  - Test POST `/api/chat` with `mode='bedrock_agent'` returns valid response
  - Verify response includes answer, sources, session_id, timestamp, processing_time
  - Test handler caching: same session_id reuses handler instance
  - Test handler caching: different session_id creates new handler instance

- **Model Endpoint:**
  - Test GET `/api/models/bedrock-agent` returns 3 models
  - Verify model list includes nova-micro, nova-lite, nova-pro
  - Verify default model matches config value

- **Conversation Flow:**
  - Send multi-turn conversation with same session_id
  - Verify conversation isolation between different session_ids

### Integration Tests
- **Full Stack Testing:**
  - Start backend server with `python backend/main.py`
  - Open frontend with `npm run dev`
  - Manually test all 4 chat modes switch correctly
  - Test Bedrock mode sends queries and receives responses
  - Test all 3 Amazon Nova models work

- **Cross-Mode Testing:**
  - Test switching from RAG Pipeline to Bedrock Agent clears conversation
  - Test switching from OpenAI Agent to Bedrock Agent clears conversation
  - Test session IDs remain unique per mode

### Edge Cases
- **Empty or Missing Fields:**
  - Bedrock returns answer with no citations
  - Bedrock returns empty answer text
  - Session ID not provided (handler should generate one)
  - Model parameter not provided (should use default)

- **Malformed Responses:**
  - Response missing ANSWER: section
  - Response missing SOURCES: section
  - Sources section contains invalid format (no "- " prefix)
  - Sources section has brackets or extra whitespace

- **AWS API Errors:**
  - Invalid/missing AWS credentials
  - KB ID doesn't exist or region mismatch
  - Model not available (not provisioned)
  - API rate limiting/throttling
  - Network timeout
  - Session expiry (if Bedrock expires sessions)

- **UI Edge Cases:**
  - Rapidly switch between modes while query is in progress
  - Send query immediately after switching to Bedrock mode
  - Clear chat while Bedrock query is in progress
  - Multiple browser tabs with different sessions

- **Conversation Edge Cases:**
  - Very long conversation (100+ turns)
  - Session cleared mid-conversation
  - Follow-up question with no prior context

## Acceptance Criteria

### Backend Handler
- [ ] `BedrockKBHandler` class created in `chatbot/handlers/bedrock_kb_handler.py`
- [ ] Handler implements `BaseHandler` interface with `handle()` and `handle_async()` methods
- [ ] Handler uses `BEDROCK_KB_ID`, `BEDROCK_AGENT_MODEL`, `AWS_REGION` from config
- [ ] Handler supports model parameter override in `__init__()`
- [ ] Handler calls AWS Bedrock `retrieve_and_generate` API correctly
- [ ] Handler maintains conversation sessions using Bedrock session management
- [ ] Handler parses Bedrock citations into sources format (doc, pages, url)
- [ ] Handler returns consistent response structure (answer, sources, response_type, action_items, thread_id, turn_count)
- [ ] Handler includes error handling with fallback message
- [ ] Handler cached per session in `_conversational_chatbots` dict

### Backend API
- [ ] `/api/chat` endpoint routes `mode='bedrock_agent'` to BedrockKBHandler
- [ ] `/api/chat` endpoint accepts `bedrock_agent_model` parameter
- [ ] `/api/chat` endpoint caches handler instances per session
- [ ] `/api/models/bedrock-agent` endpoint returns 3 Amazon Nova models
- [ ] `/api/models/bedrock-agent` endpoint returns default model from config
- [ ] `ChatMode` type includes `'bedrock_agent'` in Literal
- [ ] `ChatRequest` model includes `bedrock_agent_model` optional field

### Frontend Types
- [ ] `ChatMode` type updated to include `'bedrock_agent'`
- [ ] `BEDROCK_AGENT_MODELS` constant defined with 3 Amazon Nova models
- [ ] `ChatRequest` interface includes `bedrock_agent_model?: string`

### Frontend UI
- [ ] "Bedrock Agent" button added to Chat Mode selector (4 buttons total)
- [ ] Chat Mode selector buttons render correctly in a row
- [ ] Bedrock settings section shows when `chatMode === 'bedrock_agent'`
- [ ] Model dropdown displays 3 Amazon Nova models (nova-micro, nova-lite, nova-pro)
- [ ] Model dropdown default selection is nova-micro
- [ ] Orange info box explains: "Bedrock Agent mode is always conversational and uses AWS managed RAG with Amazon Bedrock Knowledge Base."
- [ ] No streaming toggle shown in Bedrock mode (not applicable)
- [ ] No conversational toggle shown in Bedrock mode (always conversational)
- [ ] Selected model sent in API request as `bedrock_agent_model`
- [ ] Switching to Bedrock mode clears conversation and starts new session

### Configuration
- [ ] `BEDROCK_KB_ID` added to `chatbot/config.py` with default `'371M2G58TV'`
- [ ] `BEDROCK_AGENT_MODEL` added to `chatbot/config.py` with default `'nova-micro'`
- [ ] `AWS_REGION` added to `chatbot/config.py` with default `'us-east-1'`
- [ ] Environment variables support overrides (BEDROCK_KB_ID, BEDROCK_MODEL, AWS_REGION)

### Prompt
- [ ] `bedrock_agent_prompt.py` created in `chatbot/prompts/`
- [ ] Prompt optimized for Amazon Nova models (40-50 lines)
- [ ] Prompt includes domain context (TWC, CCS, PSOC, TRS)
- [ ] Prompt includes critical domain rules (income limits, table columns, outcomes completeness)
- [ ] Prompt specifies ANSWER:/SOURCES: output format
- [ ] Prompt exported in `chatbot/prompts/__init__.py`

### Functionality
- [ ] User can select Bedrock Agent mode from UI
- [ ] User can send queries in Bedrock mode
- [ ] Responses display answer text correctly
- [ ] Sources display in source cards with document names
- [ ] All 3 Amazon Nova models (nova-micro, nova-lite, nova-pro) work
- [ ] Conversation context maintained across multiple turns
- [ ] Clear Chat resets conversation and session
- [ ] Error messages display properly when issues occur

### Testing
- [ ] Integration tests pass for `BedrockKBHandler` using real AWS Bedrock KB
- [ ] Integration tests pass for `/api/chat` endpoint with Bedrock mode
- [ ] Integration tests pass for `/api/models/bedrock-agent` endpoint
- [ ] Manual testing confirms UI works across all modes
- [ ] No regressions in existing RAG Pipeline, OpenAI Agent, or Vertex Agent modes

### Quality Metrics
- [ ] Response time < 5 seconds for typical queries
- [ ] Error rate < 5% (excluding AWS service issues)
- [ ] Source citations present in >80% of responses
- [ ] Prompt achieves >85% quality score on evaluation dataset

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# Integration tests (real AWS Bedrock KB - no mocking)
python -m pytest tests/test_bedrock_kb_handler.py -v
python -m pytest tests/test_bedrock_kb_integration.py -v

# Test Bedrock evaluation mode (validates handler logic)
python -m evaluation.run_evaluation --mode bedrock --test --limit 3

# Start backend server (verify no startup errors)
cd backend && python main.py &
BACKEND_PID=$!
sleep 5
curl http://localhost:8000/api/health
curl http://localhost:8000/api/models/bedrock-agent

# Test backend Bedrock endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is TWC?", "mode": "bedrock_agent", "bedrock_agent_model": "nova-micro"}'

# Stop backend
kill $BACKEND_PID

# Frontend build verification
cd frontend && npm run build

# Frontend dev server (manual UI testing)
cd frontend && npm run dev
# Manual steps:
# 1. Open http://localhost:3000
# 2. Click Settings (gear icon)
# 3. Select "Bedrock Agent" mode
# 4. Verify model dropdown shows 3 Nova models
# 5. Verify orange info box appears
# 6. Send test query: "What is TWC?"
# 7. Verify answer and sources display
# 8. Switch between all 4 modes - verify no errors
# 9. Test all 3 models (nova-micro, nova-lite, nova-pro)

# Run existing evaluation modes to check for regressions
python -m evaluation.run_evaluation --mode hybrid --test --limit 3
python -m evaluation.run_evaluation --mode dense --test --limit 3

# Interactive chatbot CLI (if supported)
# python interactive_chat.py
# (May need updates to support Bedrock mode)

# Full test suite
python -m pytest tests/ -v --tb=short
```

## Notes

### Design Decisions
- **Why KB only?** Simpler than supporting both KB and direct models. Matches evaluation setup. Focuses on managed RAG comparison.
- **Why no Anthropic models?** Not provisioned in AWS account. Requires use case approval. Only Amazon Nova models available.
- **Why no streaming?** Bedrock KB `retrieve_and_generate` doesn't support SSE streaming. Returns complete response.
- **Why always conversational?** Matches OpenAI/Vertex pattern. KB has built-in session support. Simplifies UI.

### Testing Philosophy
**NO MOCKING - Real Integration Tests Only**
- All tests use real AWS Bedrock KB (same setup as existing `bedrock_evaluator.py`)
- No mocked boto3 responses or simulated API calls
- Validates actual Bedrock behavior, response formats, and edge cases
- Provides confidence that the feature works with the real AWS service

### Code Reuse Opportunities
- Reuse evaluation code (`evaluation/bedrock_evaluator.py`) as reference for API calls
- Reuse or simplify model resolver logic (`evaluation/bedrock_model_resolver.py`)
- Follow existing handler patterns (`openai_agent_handler.py`, `vertex_agent_handler.py`)
- Reuse backend routing patterns from OpenAI/Vertex agent modes
- Reuse frontend UI patterns from OpenAI/Vertex settings sections

### System Prompt Optimization Strategy
The Bedrock system prompt must balance Amazon Nova model limitations with critical Texas childcare domain requirements:

**"Vertex+ Model" Approach:**
- Start with Vertex's clean structure (33 lines)
- Add critical domain rules from Custom RAG (select top 3-4 rules)
- Target 40-50 lines total
- Emphasize reasoning directive for Nova models
- Include domain context (TWC, CCS, PSOC, TRS)
- Specify structured output (ANSWER:/SOURCES:)

**Critical Domain Rules to Include:**
1. Income limits with exact amounts + BCY year specification
2. Table column parsing: rightmost = most recent year
3. Outcomes completeness: employment rates AND wage data
4. Abbreviations: full names first, then acronyms

**Testing Validation:**
- Test with income limit questions
- Test with table data questions
- Test with outcomes questions
- Test with simple yes/no questions
- Test multi-turn conversations
- Measure quality against custom RAG baseline (target: within 10%)

### Future Enhancements (Out of Scope)
- Add Bedrock direct model mode (custom retrieval, no KB)
- Support Anthropic Claude models once provisioned
- Add KB management UI (sync status, ingestion jobs)
- Advanced KB configuration (retrieval settings, chunk limits)
- Streaming support (if AWS adds SSE to retrieve_and_generate)
- Page number preservation (if AWS adds PDF metadata to KB)

### Dependencies
- Existing Bedrock KB setup (ID: `371M2G58TV`)
- AWS credentials with Bedrock permissions (`bedrock-agent-runtime:RetrieveAndGenerate`)
- `boto3` Python package (likely already installed for Kendra support)
- S3 bucket with PDFs synced to KB (24 PDFs in `cohort-tx-1` bucket)
- Amazon Nova models provisioned in `us-east-1` region

### Performance Expectations
- Response time: 2-5 seconds (AWS managed retrieval + generation)
- No client-side streaming (single response payload)
- Session caching: Reuse handler instances per session
- No local embeddings/reranking (all managed by AWS)

### Security Considerations
- AWS credentials via environment variables (not hardcoded)
- Read-only KB access (no data upload in this feature)
- No additional logging of queries/responses (AWS CloudWatch handles logging)
- Session IDs remain client-side (not persisted server-side beyond runtime)

### Debugging Tips
- Use `debug=True` in handler to see raw Bedrock response
- Check `BEDROCK_KB_ID` environment variable is set correctly
- Verify AWS region matches KB region (`us-east-1`)
- Use `boto3` exceptions to catch specific AWS errors (ThrottlingException, ResourceNotFoundException)
- Test with simple query first ("What is TWC?") before complex queries
- Compare Bedrock responses to evaluation mode results for consistency
