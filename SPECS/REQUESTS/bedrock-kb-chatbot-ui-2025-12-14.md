# Feature Request: Bedrock Knowledge Base Integration

**Date:** 2025-12-14
**Status:** Refined

## Overview
Add Amazon Bedrock Knowledge Base as a new chat mode in the UI and backend, following the same pattern as existing OpenAI Agent and Vertex Agent modes.

## Problem Statement
The evaluation system supports Bedrock KB for testing (`bedrock` mode), but the chatbot UI and interactive interface don't expose this capability to users. Users should be able to compare AWS managed RAG (Bedrock KB) against the custom RAG pipeline and other agent modes directly in the chat interface.

## Users & Stakeholders
- Primary Users: Developers and evaluators testing different RAG approaches
- Use Case: Comparing managed AWS RAG performance against custom pipeline
- Permissions: No special permissions required (uses existing AWS credentials)

## Functional Requirements

### 1. Backend Handler
- Create `BedrockKBHandler` in `chatbot/handlers/bedrock_kb_handler.py`
- Use existing Bedrock KB setup (ID: `371M2G58TV`)
- Call AWS Bedrock `retrieve_and_generate` API
- Support conversation continuity via session management
- Handle model selection (nova-micro, nova-lite, nova-pro)

### 2. API Integration
- Add `bedrock_agent` to `ChatMode` type
- Support `bedrock_agent_model` parameter in `ChatRequest`
- Add `/api/models/bedrock-agent` endpoint for model list
- Cache handler instances per session (like OpenAI/Vertex)
- Return citations from Bedrock KB responses

### 3. UI Components
- Add "Bedrock Agent" button to Chat Mode selector
- Add Bedrock model dropdown (3 Amazon models)
- Add info box explaining managed RAG behavior
- No streaming toggle (not supported)
- No conversational toggle (always conversational)
- No retrieval mode selector (uses KB's retrieval)

### 4. Type Definitions
- Add `bedrock_agent` to `ChatMode` union type
- Add `BEDROCK_AGENT_MODELS` constant array
- Add `bedrock_agent_model` to `ChatRequest` interface
- Update all relevant type files

## User Flow

1. User opens chat interface
2. User clicks Settings button
3. User selects "Bedrock Agent" from Chat Mode selector
4. UI shows:
   - Model dropdown with 3 Amazon Nova models
   - Orange info box: "Bedrock Agent mode is always conversational and uses AWS managed RAG with Amazon Bedrock Knowledge Base."
5. User selects model (default: nova-micro)
6. User sends question
7. Backend routes to `BedrockKBHandler`
8. Handler calls Bedrock `retrieve_and_generate`
9. Response displays with answer and citations
10. Conversation history maintained via session

## Acceptance Criteria

### Backend
- [ ] `BedrockKBHandler` created with `handle()` and `handle_async()` methods
- [ ] Handler uses `BEDROCK_KB_ID` from config/environment
- [ ] Handler supports model parameter (nova-micro/lite/pro)
- [ ] Handler maintains conversation sessions (like OpenAI/Vertex)
- [ ] Handler parses Bedrock citations into sources format
- [ ] `/api/chat` endpoint routes `mode='bedrock_agent'` to handler
- [ ] `/api/models/bedrock-agent` endpoint returns 3 models + default
- [ ] Handler cached per session in `_conversational_chatbots`

### Frontend
- [ ] "Bedrock Agent" button added to Chat Mode selector (4 buttons total)
- [ ] Bedrock settings section shows when `chatMode === 'bedrock_agent'`
- [ ] Model dropdown displays 3 Amazon Nova models
- [ ] Orange info box explains managed RAG behavior
- [ ] No streaming toggle shown (not applicable)
- [ ] No conversational toggle shown (always on)
- [ ] Selected model sent in API request as `bedrock_agent_model`
- [ ] Citations displayed in source cards

### Configuration
- [ ] `BEDROCK_KB_ID` added to `chatbot/config.py` (default: `371M2G58TV`)
- [ ] `BEDROCK_AGENT_MODEL` added to config (default: `nova-micro`)
- [ ] `AWS_REGION` configurable (default: `us-east-1`)
- [ ] Environment variables documented in README

### Types
- [ ] `ChatMode` includes `'bedrock_agent'`
- [ ] `BEDROCK_AGENT_MODELS` constant defined
- [ ] `ChatRequest` includes `bedrock_agent_model?: string`
- [ ] All type files updated consistently

## User Experience

### Interface
- **Platform**: Web UI (Next.js frontend)
- **Entry Point**: Model Settings dropdown (gear icon)
- **Layout**: 4-button Chat Mode selector (RAG Pipeline | OpenAI Agent | Vertex Agent | Bedrock Agent)

### Key Interactions
1. **Mode Selection**: Click "Bedrock Agent" button → UI updates to show Bedrock settings
2. **Model Selection**: Dropdown with 3 options (Nova Micro/Lite/Pro)
3. **Info Display**: Orange box explains AWS managed RAG (matches Vertex green box pattern)
4. **Chat**: Standard message input/output (same as other modes)
5. **Sources**: Citations displayed in familiar source card format

### Feedback
- **Success**: Response with answer and source citations
- **Error**: Standard error message with fallback to support phone number
- **Loading**: "Processing..." state during API call (no streaming)

## Technical Requirements

### Integration
- **AWS SDK**: Use `boto3` for Bedrock Agent Runtime
- **API**: `bedrock-agent-runtime:retrieve_and_generate`
- **Authentication**: AWS credentials from environment/profile
- **Knowledge Base**: Existing KB `371M2G58TV`
- **Vector Store**: OpenSearch Serverless (already configured)

### Performance
- **Response Time**: ~2-5 seconds (AWS managed retrieval + generation)
- **No Streaming**: Single response payload (like OpenAI/Vertex)
- **Session Caching**: Reuse handler instances per session

### Security
- **Credentials**: AWS credentials via environment variables
- **KB Access**: Read-only access to existing KB
- **No Data Upload**: Uses existing synced PDFs in S3

### Platform
- **Backend**: Python/FastAPI
- **Frontend**: Next.js/React/TypeScript
- **AWS Region**: us-east-1 (default, configurable)

## Data Model

### Storage
- **Session State**: In-memory handler cache (`_conversational_chatbots`)
- **Conversation History**: Maintained by Bedrock KB session management
- **No Persistence**: Sessions cleared on server restart

### Retention
- **Session Lifetime**: Duration of user session (until Clear Chat clicked)
- **Cache Cleanup**: Manual clear or server restart

### Privacy
- **AWS Processing**: Queries processed by AWS Bedrock (AWS privacy policy applies)
- **No Logging**: No additional logging of queries/responses

## Edge Cases & Error Handling

### Missing Environment Variables
**Case**: `BEDROCK_KB_ID` not set
**Behavior**: Handler initialization fails with clear error message

### AWS Credential Issues
**Case**: Invalid/missing AWS credentials
**Behavior**: Return error: "Unable to connect to Bedrock. Please check AWS configuration."

### Knowledge Base Not Found
**Case**: KB ID doesn't exist or region mismatch
**Behavior**: Return error with fallback support message

### Model Not Available
**Case**: Selected model not provisioned in region
**Behavior**: Fall back to default (nova-micro) or show specific error

### API Rate Limits
**Case**: AWS API throttling
**Behavior**: Return error with retry suggestion

### Empty Citations
**Case**: Bedrock returns no sources
**Behavior**: Display answer with empty sources array (valid scenario)

### Session Expiry
**Case**: User session cleared or expired
**Behavior**: Start new session on next query (transparent to user)

## Dependencies

### Requires
- Existing Bedrock KB setup (`371M2G58TV`)
- AWS credentials with Bedrock permissions
- `boto3` Python package installed
- S3 bucket with PDFs synced to KB

### Blocks
- None (independent feature addition)

### Related
- Evaluation system already uses Bedrock KB
- Can reuse model resolver logic from `evaluation/bedrock_model_resolver.py`

## Out of Scope

### NOT Included
- ❌ Bedrock direct model calls (without KB) - only KB managed RAG
- ❌ Streaming responses - Bedrock KB doesn't support SSE streaming
- ❌ Conversational toggle - always conversational (like OpenAI/Vertex)
- ❌ Retrieval mode selector - uses KB's built-in retrieval
- ❌ Custom chunking/reranking - managed by AWS
- ❌ Anthropic Claude models - not provisioned, only Amazon Nova models
- ❌ Page number citations - Bedrock KB doesn't preserve PDF metadata
- ❌ S3 sync UI - use existing CLI/SDK for KB ingestion

## Success Metrics

### Functional Success
- User can select Bedrock Agent mode and send queries
- Responses return with citations from KB
- Conversations maintain context across turns
- All 3 Amazon models selectable and functional

### Quality Metrics
- Response time < 5 seconds for typical queries
- Error rate < 5% (excluding AWS service issues)
- Source citations present in >80% of responses

### Comparison Value
- Enables side-by-side comparison of:
  - Custom RAG (hybrid/dense) vs AWS managed RAG
  - Bedrock vs OpenAI vs Vertex agent approaches
- Supports evaluation workflow improvements

## Implementation Notes

### File Structure
```
chatbot/handlers/
├── bedrock_kb_handler.py         # NEW: Bedrock KB handler
├── openai_agent_handler.py       # Reference pattern
└── vertex_agent_handler.py       # Reference pattern

backend/api/
├── routes.py                     # Add bedrock_agent routing
└── models.py                     # Update ChatRequest type

frontend/
├── components/
│   ├── ChatInterface.tsx         # Add bedrock state
│   └── ModelSettings.tsx         # Add bedrock UI section
└── lib/
    ├── types.ts                  # Add bedrock types
    └── api.ts                    # Update API calls

chatbot/
└── config.py                     # Add BEDROCK_KB_ID, BEDROCK_AGENT_MODEL

evaluation/
├── bedrock_evaluator.py          # Reference for KB API calls
└── bedrock_model_resolver.py    # Reference for model handling
```

### Code Reuse
- Evaluation code provides working Bedrock KB API examples
- Model resolver logic can be simplified (only 3 models)
- Handler pattern matches OpenAI/Vertex agents closely

### System Prompt Optimization

**CRITICAL**: The Bedrock system prompt must be carefully optimized based on analysis of existing prompts and Amazon Nova model capabilities.

#### Existing Prompt Analysis

**Custom RAG Prompt** (`response_generation_prompt.py`):
- **Strengths**: Extremely detailed domain rules, handles complex edge cases (table parsing, BCY years, outcomes completeness), specific response style guidance
- **Weaknesses**: Very long (77 lines), may overwhelm simpler models, specific to custom retrieval format
- **Key Elements**: Abbreviations glossary, exact income formatting, table column parsing (rightmost = most recent), outcomes data completeness (employment + wage data), response length matching

**OpenAI Agent Prompt** (`openai_agent_prompt.py`):
- **Strengths**: Concise (36 lines), clean output format (ANSWER:/SOURCES:), emphasizes reasoning before answering
- **Weaknesses**: Lacks domain-specific rules, no guidance on complex data, minimal Texas context
- **Key Elements**: 1-4 sentence brevity, structured output, query injection, "ensure reasoning before final answer"

**Vertex Agent Prompt** (`vertex_agent_prompt.py`):
- **Strengths**: Balanced approach (34 lines), includes domain context section (TWC, CCS, PSOC, Texas Rising Star), clean output format
- **Weaknesses**: Still missing critical domain rules (income formats, table parsing), no abbreviation guidance
- **Key Elements**: Domain context list, 1-3 sentence conciseness, retrieval tool mention, structured output

#### Bedrock-Specific Constraints

1. **Amazon Nova Models** (micro/lite/pro):
   - Less powerful than GPT-4 or Claude Sonnet
   - Benefit from clear, simple instructions
   - Need explicit reasoning directives
   - Avoid overly complex multi-layered rules

2. **Managed Retrieval**:
   - No control over chunking or context format
   - Citations may differ from custom RAG
   - Cannot rely on custom chunk metadata
   - Less control over retrieved passages

3. **Session-Based Conversations**:
   - Built-in Bedrock session management
   - Similar to OpenAI threads
   - No need for explicit history injection
   - Context continuation handled by KB

#### Recommended Prompt Strategy: "Vertex+ Model"

**Approach**: Start with Vertex's clean structure, add critical domain rules from Custom RAG, optimize for Nova capabilities.

**Target Length**: 40-50 lines (between OpenAI's 36 and Custom RAG's 77)

**Required Sections**:

1. **Role Definition** (1-2 lines)
   - "You are a Texas childcare assistance expert"
   - Position as authoritative but helpful

2. **Core Behavioral Rules** (4-6 lines)
   - Use ONLY retrieved information
   - Concise responses (1-4 sentences based on complexity)
   - Don't speculate if info not found
   - Ask for clarification if ambiguous
   - **Reasoning directive**: "Think through retrieved information before answering" (critical for Nova)

3. **Domain Context** (6-8 lines)
   - TWC programs and Child Care Services (CCS)
   - Texas Rising Star quality rating
   - Parent Share of Cost (PSOC) calculations
   - Provider requirements and reimbursement
   - Key organizations: TWC, HHSC, DFPS
   - Common abbreviations (TWC, CCS, BCY, PSOC, TRS)

4. **Critical Domain-Specific Rules** (10-12 lines condensed from Custom RAG):
   - **Income limits**: Always include exact amounts + year/BCY specification
   - **Table data**: "For tables with year columns, the RIGHTMOST column is the most recent year"
   - **Outcomes data**: "When answering about outcomes or effectiveness, include ALL data types: employment rates AND wage/earnings data - never omit either"
   - **Abbreviations**: Use full organization names on first mention, then acronyms
   - **Application processes**: List steps in sequential order
   - **Missing information**: Explicitly state "I don't have information about..." rather than guessing

5. **Response Style Guidance** (4-6 lines):
   - Match length to question complexity
   - Simple/yes-no questions: 1-2 sentences, start with Yes/No
   - Enumeration questions: Provide complete lists
   - Policy questions: Include all criteria and conditions
   - Use markdown lists only for 3+ distinct items

6. **Output Format** (8-10 lines):
   ```
   ANSWER:
   [Your response here]

   SOURCES:
   - [filename1.pdf]
   - [filename2.pdf]
   ```
   - List each source on own line with "- " prefix
   - Only include files directly contributing to answer
   - Use "- None" if no sources used

**What to EXCLUDE** (avoid overwhelming Nova):
- ❌ Overly granular chunk format rules (managed by Bedrock)
- ❌ Explicit history injection patterns (handled by sessions)
- ❌ Complex multi-hop reasoning instructions (Nova limitation)
- ❌ Excessive edge case handling (keep to critical 3-4 rules)

**Implementation Location**: Create `chatbot/prompts/bedrock_agent_prompt.py`

**Testing Validation**:
- Test with income limit questions (verify exact amounts + BCY)
- Test with table data questions (verify year column parsing)
- Test with outcomes questions (verify employment AND wage data inclusion)
- Test with simple yes/no questions (verify 1-2 sentence responses)
- Test with multi-turn conversations (verify context retention)
- Test abbreviation handling (TWC, CCS, PSOC full names)

**Iterative Refinement**:
1. Start with Vertex+ template
2. Test with 10-15 evaluation questions
3. Identify common failure patterns
4. Add specific rules to address top 3 failure modes
5. Re-test and measure improvement
6. Repeat until quality matches custom RAG baseline (within 10%)

**Expected Outcome**:
A 40-50 line prompt that balances Nova model limitations with critical Texas childcare domain requirements, achieving >85% quality score on evaluation dataset while maintaining conciseness and clarity.

### Testing
- Unit tests for handler initialization and API calls
- Integration test for full request/response cycle
- Manual testing with all 3 models
- Conversation continuity testing (multi-turn)

## Notes

### Design Decisions
- **Why KB only?** Simpler than supporting both KB and direct models. Matches evaluation setup.
- **Why no Anthropic models?** Not provisioned in AWS account. Requires use case approval.
- **Why no streaming?** Bedrock KB `retrieve_and_generate` doesn't support SSE streaming.
- **Why always conversational?** Matches OpenAI/Vertex pattern. KB has built-in session support.

### Future Enhancements (Out of Scope)
- Add Bedrock direct model mode (custom retrieval)
- Support Anthropic models once provisioned
- Add KB management UI (sync, status)
- Advanced KB configuration (retrieval settings)

### References
- Existing evaluation code: `evaluation/bedrock_evaluator.py`
- Bedrock KB docs: `SPECS/DOC/bedrock_kb_evaluator.md`
- AWS Bedrock Agent Runtime API docs
