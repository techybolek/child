# Feature Request: Retrieval Mode Selection

**Date:** 2025-12-01
**Status:** Refined

## Overview

Allow users to select between `dense`, `hybrid`, or `kendra` retrieval modes from the frontend settings panel. The selected mode is passed to the backend with each API call, overriding the default configuration.

## Problem Statement

Currently, retrieval mode is fixed at the server level via the `RETRIEVAL_MODE` environment variable. Users cannot experiment with different retrieval strategies without restarting the backend. This limits the ability to compare retrieval quality during development and demos.

## Users & Stakeholders

- **Primary Users:** Developers, evaluators, demo presenters
- **Permissions:** None required (all users can access)

## Functional Requirements

1. **Frontend displays retrieval mode selector** in ModelSettings panel
2. **Default mode is `dense`** when no selection is made
3. **All 3 options always visible** (dense, hybrid, kendra) regardless of backend configuration
4. **Selection passed with each `/api/chat` request** as `retrieval_mode` parameter
5. **Backend respects per-request override** when provided, falls back to config default otherwise
6. **Kendra mode uses unified LangGraph pipeline** (requires creating KendraRetriever)

## User Flow

1. User opens chat interface
2. User clicks settings gear icon
3. Settings panel expands showing retrieval mode selector (default: Dense)
4. User selects "Hybrid" or "Kendra"
5. User sends a question
6. Frontend includes `retrieval_mode: "hybrid"` in API request
7. Backend routes to appropriate retriever
8. Response returns as normal

## Acceptance Criteria

- [ ] Retrieval mode selector visible in ModelSettings panel
- [ ] Default selection is "Dense" on page load
- [ ] Selecting a mode updates UI immediately
- [ ] API request includes `retrieval_mode` field when mode selected
- [ ] Backend accepts `retrieval_mode` in ChatRequest
- [ ] Backend uses specified retriever for that request
- [ ] Kendra mode works through LangGraph pipeline (not legacy handler)
- [ ] Error from Kendra (e.g., no AWS credentials) returns clear error message
- [ ] Mode selection does NOT persist across page refresh (resets to default)

## User Experience

### Interface

**Location:** ModelSettings panel (collapsible dropdown from gear icon)

**Placement:** New section ABOVE the provider selector (retrieval mode is more fundamental than LLM choice)

**UI Component:** Radio button group (toggle buttons) - not a dropdown

```
┌─────────────────────────────────────┐
│ ⚙️ Settings                     [×] │
├─────────────────────────────────────┤
│                                     │
│ Retrieval Mode                      │
│ ┌─────────┬─────────┬─────────┐    │
│ │  Dense  │ Hybrid  │ Kendra  │    │
│ │   ●     │         │         │    │
│ └─────────┴─────────┴─────────┘    │
│                                     │
│ ─────────────────────────────────── │
│                                     │
│ Provider                            │
│ ┌─────────────────────────────┐    │
│ │ Groq                      ▼ │    │
│ └─────────────────────────────┘    │
│                                     │
│ Generator Model                     │
│ ...                                 │
└─────────────────────────────────────┘
```

**Visual Design:**
- Three equal-width buttons in a row
- Selected button: `bg-blue-600 text-white`
- Unselected buttons: `bg-gray-100 text-gray-700 hover:bg-gray-200`
- Rounded corners on outer edges only (pill-shaped group)
- Subtle border: `border border-gray-300`

**Labels:**
| Value | Label | Tooltip (title attr) |
|-------|-------|----------------------|
| `dense` | Dense | Semantic search using embeddings |
| `hybrid` | Hybrid | Combines semantic + keyword search |
| `kendra` | Kendra | AWS Kendra managed search |

### Feedback

- **Success:** No explicit feedback needed (mode applied silently)
- **Kendra Error:** Red error banner: "Kendra retrieval failed: [error message]. Try Dense or Hybrid mode."

## Technical Requirements

### Frontend Changes

**1. lib/types.ts**
```typescript
// Add to ChatRequest interface
retrieval_mode?: 'dense' | 'hybrid' | 'kendra'

// Add type
type RetrievalMode = 'dense' | 'hybrid' | 'kendra'
```

**2. lib/api.ts**
```typescript
// Update askQuestion signature
async askQuestion(
  question: string,
  sessionId?: string,
  models?: {
    provider?: string
    llm_model?: string
    reranker_model?: string
    intent_model?: string
    retrieval_mode?: string  // ADD
  },
  conversationalMode?: boolean
): Promise<ChatResponse>
```

**3. components/ChatInterface.tsx**
```typescript
// Add state
const [retrievalMode, setRetrievalMode] = useState<'dense' | 'hybrid' | 'kendra'>('dense')

// Update handleSubmit to include retrievalMode in API call
// Pass retrievalMode and setRetrievalMode to ModelSettings
```

**4. components/ModelSettings.tsx**
```typescript
// Add props
retrievalMode: 'dense' | 'hybrid' | 'kendra'
onRetrievalModeChange: (mode: 'dense' | 'hybrid' | 'kendra') => void

// Add UI component (toggle button group)
```

### Backend Changes

**1. backend/api/models.py**
```python
class ChatRequest(BaseModel):
    # ... existing fields ...
    retrieval_mode: Optional[str] = Field(
        None,
        description="Retrieval mode: 'dense', 'hybrid', or 'kendra'"
    )
```

**2. backend/api/routes.py**
- Pass `retrieval_mode` to chatbot constructor when creating custom instance
- Validate that retrieval_mode is one of: `dense`, `hybrid`, `kendra`

**3. chatbot/chatbot.py**
```python
def __init__(self, ..., retrieval_mode=None):
    self.retrieval_mode = retrieval_mode
    # Pass through state
```

**4. chatbot/graph/state.py**
```python
# Add to RAGState / ConversationalRAGState
retrieval_mode_override: str | None
```

**5. chatbot/graph/nodes/retrieve.py**
```python
def retrieve_node(state: dict) -> dict:
    # Check for override first
    mode = state.get("retrieval_mode_override") or config.RETRIEVAL_MODE

    if mode == 'kendra':
        retriever = KendraRetriever()
    elif mode == 'hybrid':
        retriever = QdrantHybridRetriever()
    else:
        retriever = QdrantRetriever()
    # ...
```

**6. NEW: chatbot/kendra_retriever.py**

Create a new `KendraRetriever` class that wraps AWS Kendra with the same interface as `QdrantRetriever`:

```python
class KendraRetriever:
    """AWS Kendra retriever with same interface as QdrantRetriever."""

    def __init__(self):
        from langchain_aws import AmazonKendraRetriever
        self.retriever = AmazonKendraRetriever(
            index_id=config.KENDRA_INDEX_ID,
            region_name=config.KENDRA_REGION,
            top_k=config.RETRIEVAL_TOP_K
        )

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """Search Kendra and return chunks in standard format."""
        docs = self.retriever.get_relevant_documents(query)
        return self._convert_to_chunks(docs[:top_k or config.RETRIEVAL_TOP_K])

    def _convert_to_chunks(self, docs) -> list[dict]:
        """Convert Kendra docs to chunk dict format."""
        # Map to same format as Qdrant chunks
```

### Integration

- **Qdrant:** Already configured, no changes
- **AWS Kendra:** Requires existing AWS credentials in environment
- **LangGraph:** KendraRetriever integrates into existing pipeline

### Performance

- No significant performance impact (retriever selection is O(1))
- Kendra may have different latency characteristics than Qdrant

### Security

- No new authentication required
- AWS credentials already managed server-side
- No sensitive data exposed to frontend

### Platform

- Web only (Next.js frontend)

## Data Model

### Storage

- **Frontend:** `retrievalMode` state in React component (memory only)
- **Backend:** No persistence (per-request parameter)

### Retention

- None (stateless per request)

### Privacy

- No PII involved
- No compliance considerations

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| Kendra not configured (no AWS creds) | Backend returns error: "Kendra is not configured. Check AWS credentials." → Frontend shows error banner |
| Invalid retrieval_mode value | Backend validates, returns 400: "Invalid retrieval_mode. Must be: dense, hybrid, kendra" |
| Kendra rate limit exceeded | Backend returns error with AWS message → Frontend shows error banner |
| Network timeout to Kendra | Backend returns error → Frontend shows error banner with retry option |
| Empty results from any retriever | Proceed normally (generator handles empty context) |

## Dependencies

### Requires

- Existing Qdrant collection (`tro-child-hybrid-v1`)
- AWS Kendra index (for kendra mode)
- `langchain_aws` package (already in requirements)

### Blocks

- Nothing (additive feature)

## Out of Scope

- OpenAI retrieval mode (explicitly excluded per request)
- Persisting mode selection across sessions
- Per-user mode preferences
- Mode availability endpoint (always show all 3)
- Automatic fallback if Kendra fails

## Success Metrics

- Feature works end-to-end for all 3 modes
- No regression in existing dense/hybrid functionality
- Clear error messages when Kendra unavailable

## Implementation Notes

### Recommended Order

1. **Backend first:** Add `retrieval_mode` to ChatRequest, create KendraRetriever, update retrieve_node
2. **Test backend:** Verify all 3 modes work via curl/Postman
3. **Frontend:** Add UI component and wire up API calls
4. **Integration test:** End-to-end testing through UI

### Files to Modify

| File | Change |
|------|--------|
| `frontend/lib/types.ts` | Add `retrieval_mode` to ChatRequest |
| `frontend/lib/api.ts` | Pass retrieval_mode in request |
| `frontend/components/ChatInterface.tsx` | Add state, pass to ModelSettings |
| `frontend/components/ModelSettings.tsx` | Add toggle button group UI |
| `backend/api/models.py` | Add retrieval_mode field |
| `backend/api/routes.py` | Pass to chatbot, add validation |
| `chatbot/chatbot.py` | Accept and propagate retrieval_mode |
| `chatbot/graph/state.py` | Add retrieval_mode_override field |
| `chatbot/graph/nodes/retrieve.py` | Check override, route to retriever |

### New Files

| File | Purpose |
|------|---------|
| `chatbot/kendra_retriever.py` | KendraRetriever class for LangGraph integration |

### Refactoring Considerations

The existing `KendraHandler` in `chatbot/handlers/kendra_handler.py` duplicates retrieval + generation logic. After this feature:
- `KendraRetriever` handles retrieval only
- LangGraph pipeline handles reranking + generation
- Consider deprecating `KendraHandler` (keep for backward compatibility with `interactive_chat.py --mode kendra`)

### Config Update

Update `chatbot/config.py` docstring:
```python
# RETRIEVAL_MODE: 'dense', 'hybrid', or 'kendra'
# Can be overridden per-request via API
RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'dense')
```
