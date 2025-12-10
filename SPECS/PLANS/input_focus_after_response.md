# Bug: Query Input Loses Focus After Response Completes

## Bug Description
After the user submits a query and the AI response is fully received, the query input textarea loses focus. Users expect that after the response appears, they can immediately start typing their next question without having to click back into the input field. Currently, the focus is lost, requiring an extra click to continue the conversation.

**Expected behavior:** Input field retains or regains focus after response completion, allowing continuous typing.

**Actual behavior:** Input field loses focus when response completes. User must click to refocus before typing the next question.

## Problem Statement
The `InputBar` component lacks focus management when its disabled state transitions from `true` to `false` after a response completes. When `isLoading` becomes `false`, the textarea becomes enabled again but focus is not programmatically restored.

## Solution Statement
Add a `useEffect` hook in `InputBar.tsx` that watches the `isLoading` prop and restores focus to the textarea when loading transitions from `true` to `false`. This is a minimal, surgical fix that addresses the root cause directly without introducing unnecessary complexity.

## Steps to Reproduce
1. Start the frontend application (`cd frontend && npm run dev`)
2. Navigate to `http://localhost:3000`
3. Click into the query input textarea
4. Type a question (e.g., "What is the income limit?")
5. Press Enter or click Send
6. Wait for the response to complete (loading spinner disappears)
7. **Observe:** The textarea is no longer focused - cursor is not in the input
8. Attempt to type - nothing happens until you click the input again

## Root Cause Analysis
The bug originates from the interaction between `ChatInterface.tsx` and `InputBar.tsx`:

1. **State Flow:**
   - User submits query → `handleSubmit()` sets `isLoading = true`
   - `InputBar` receives `isLoading={true}` → textarea gets `disabled={true}`
   - Response completes → `setIsLoading(false)`
   - `InputBar` receives `isLoading={false}` → textarea gets `disabled={false}`

2. **Missing Focus Restoration:**
   - When `disabled` changes from `true` to `false`, the browser doesn't automatically restore focus
   - `InputBar.tsx` has no `useEffect` watching `isLoading` to restore focus
   - The existing `useEffect` (lines 43-48) only handles textarea height, not focus

3. **Why Focus is Lost:**
   - Before submit: User has focus in textarea
   - During loading: `disabled={true}` removes focus from the element (browser behavior)
   - After loading: `disabled={false}` enables the element but doesn't restore focus

## Relevant Files
Use these files to fix the bug:

- **`frontend/components/InputBar.tsx`** - The component containing the textarea that loses focus. This is where the fix will be implemented by adding focus restoration logic.
- **`frontend/components/ChatInterface.tsx`** - Parent component that passes `isLoading` prop. No changes needed here, but understanding the state flow is important.
- **`.claude/commands/test_e2e.md`** - E2E test runner instructions. Read this to understand the E2E test format.
- **`.claude/commands/e2e/test_basic_query.md`** - Example E2E test. Read this as a template for the new focus test.

### New Files
- **`.claude/commands/e2e/test_input_focus_after_response.md`** - New E2E test to validate the focus fix works correctly.

## Step by Step Tasks

### 1. Add Focus Restoration Logic to InputBar
- Open `frontend/components/InputBar.tsx`
- Add a `useRef` to track the previous loading state: `const prevIsLoadingRef = useRef(isLoading)`
- Add a `useEffect` that:
  - Compares `prevIsLoadingRef.current` with current `isLoading`
  - When transitioning from `true` to `false` (loading just finished), call `textareaRef.current?.focus()`
  - Update `prevIsLoadingRef.current = isLoading` at the end
- The effect should have `[isLoading]` as its dependency array

Example implementation:
```tsx
// Track previous loading state for focus restoration
const prevIsLoadingRef = useRef(isLoading)

// Restore focus when loading completes
useEffect(() => {
  // Focus the input when loading transitions from true to false
  if (prevIsLoadingRef.current && !isLoading) {
    textareaRef.current?.focus()
  }
  prevIsLoadingRef.current = isLoading
}, [isLoading])
```

### 2. Create E2E Test for Input Focus
- Read `.claude/commands/e2e/test_basic_query.md` to understand the test format
- Create a new E2E test file at `.claude/commands/e2e/test_input_focus_after_response.md`
- The test should:
  1. Navigate to the application
  2. Enter a query and submit
  3. Wait for the response to complete
  4. **Verify** the input textarea has focus (document.activeElement should be the textarea)
  5. Type additional characters and verify they appear in the input
  6. Take screenshots at key moments

### 3. Run Validation Commands
- Execute all validation commands listed below to confirm the fix works with zero regressions

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

```bash
# 1. Verify no TypeScript errors in the modified file
cd frontend && npx tsc --noEmit

# 2. Verify no lint errors
cd frontend && npm run lint

# 3. Start frontend for manual/E2E testing
cd frontend && npm run dev

# 4. Manual reproduction test (in browser):
#    - Navigate to http://localhost:3000
#    - Type "What is the income limit?" and press Enter
#    - Wait for response
#    - Verify cursor is blinking in the input field
#    - Type "abc" immediately - should appear in input without clicking

# 5. E2E test (after creating the test file):
#    /test_e2e random_hex test_e2e .claude/commands/e2e/test_input_focus_after_response.md
```

## Notes
- This is a common UX pattern in chat interfaces - the input should always regain focus after the AI responds
- The fix uses a ref to track previous state rather than another state variable to avoid extra re-renders
- No external libraries are needed for this fix
- The fix is backward compatible and has no impact on any other functionality
- Consider edge case: If user clicks elsewhere during loading, we might be stealing focus. However, this is standard chat interface behavior and most users expect to continue typing after response completion.
