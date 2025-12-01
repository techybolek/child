# Bug: Clear Conversation Keeps Same Backend Thread

## Bug Description
When the user clicks the "Clear" button in the UI while in conversational mode, the frontend clears the local message history but continues sending the same `session_id` to the backend. The backend uses this `session_id` as the key for its cached chatbot instances (`_conversational_chatbots`), so the conversation memory persists on the server side despite the UI appearing cleared.

**Symptoms:**
- User clicks "Clear" → UI shows empty conversation
- User asks new question → Backend responds with context from previous (cleared) conversation
- Follow-up questions still resolve pronouns/references from the "cleared" conversation

**Expected behavior:**
- Clicking "Clear" should start a completely fresh conversation with no memory of previous turns

**Actual behavior:**
- Backend continues the same thread because `session_id` never changes

## Problem Statement
The frontend generates a `session_id` once at component mount and never regenerates it when the user clears the conversation. The backend caches chatbot instances by `session_id`, so clearing the UI messages does nothing to reset the backend's conversation memory.

## Solution Statement
When the user clicks "Clear" in conversational mode, the frontend should generate a new `session_id`. This causes the backend to create a new chatbot instance for the new session, effectively resetting the conversation memory.

Two approaches considered:
1. **Frontend-only fix (chosen):** Regenerate `session_id` on clear - simple, no backend changes needed
2. **Backend endpoint:** Add `/api/session/clear` endpoint - more complex, requires frontend + backend changes

The frontend-only fix is sufficient since generating a new `session_id` naturally causes the backend to create a fresh chatbot instance for the new conversation.

## Steps to Reproduce
1. Enable conversational mode in the UI (Settings → toggle "Conversational Mode" on)
2. Ask: "What is CCS?"
3. Ask: "How do I apply for it?" → Should correctly resolve "it" to CCS
4. Click "Clear" button
5. Confirm clear in dialog
6. Ask: "How do I apply for it?" → BUG: Still resolves "it" to CCS from cleared conversation

## Root Cause Analysis
In `frontend/components/ChatInterface.tsx`:

```typescript
// Line 21: session_id is generated ONCE at mount, never regenerated
const [sessionId] = useState<string>(generateId())

// Lines 138-144: handleClearConversation only clears local state
const handleClearConversation = () => {
  if (confirm('Are you sure you want to clear the conversation?')) {
    setMessages([])      // ← Clears UI messages
    setError(null)
    setLastQuestion('')
    // MISSING: Does not regenerate sessionId
  }
}
```

The `sessionId` is created once via `useState<string>(generateId())` with no setter exposed. When clear is triggered, only `messages`, `error`, and `lastQuestion` are reset.

In `backend/api/routes.py`:

```python
# Line 18: Backend caches chatbot instances by session_id
_conversational_chatbots: Dict[str, Any] = {}

# Lines 182-196: Session lookup/create logic
if request.conversational_mode:
    if session_id in _conversational_chatbots:
        chatbot = _conversational_chatbots[session_id]  # ← Reuses old instance
```

The backend correctly caches by `session_id`, but since the frontend never changes the `session_id`, the old chatbot with its conversation memory is always reused.

## Relevant Files
Use these files to fix the bug:

- **`frontend/components/ChatInterface.tsx`** - Contains the `sessionId` state and `handleClearConversation` function. The fix changes the state declaration from `useState` to allow updating, and modifies `handleClearConversation` to regenerate the session ID.

- **`frontend/lib/utils.ts`** - Contains the `generateId()` function used to create session IDs. No changes needed, just referenced.

## Step by Step Tasks

### 1. Update sessionId State Declaration
- Change line 21 from:
  ```typescript
  const [sessionId] = useState<string>(generateId())
  ```
  to:
  ```typescript
  const [sessionId, setSessionId] = useState<string>(generateId())
  ```
- This exposes the setter function needed to regenerate the session ID

### 2. Update handleClearConversation Function
- Modify the `handleClearConversation` function (lines 138-144) to also regenerate the session ID:
  ```typescript
  const handleClearConversation = () => {
    if (confirm('Are you sure you want to clear the conversation?')) {
      setMessages([])
      setError(null)
      setLastQuestion('')
      setSessionId(generateId())  // ← Add this line
    }
  }
  ```

### 3. Manual Validation
- Start the frontend and backend
- Enable conversational mode
- Test the reproduction steps to confirm the bug is fixed:
  1. Ask "What is CCS?"
  2. Ask "How do I apply for it?" → Should resolve correctly
  3. Click "Clear"
  4. Ask "How do I apply for it?" → Should NOT resolve "it" (fresh conversation)

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

- `cd frontend && npm run build` - Ensure TypeScript compiles without errors
- `cd frontend && npm run lint` - Ensure no lint errors introduced

## Notes
- No new libraries required
- Backend change is not necessary since a new `session_id` naturally creates a fresh chatbot instance
- The old cached chatbot instances in `_conversational_chatbots` will remain in memory but are orphaned. This is acceptable for a prototype; in production, consider adding TTL-based cleanup or a clear endpoint.
- The fix is minimal (2 lines changed) and surgical - only affects the clear functionality
