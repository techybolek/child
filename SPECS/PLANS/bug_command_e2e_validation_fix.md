# Bug Command: E2E Validation Section Fix

## Problem

When the bug.md command generates plans for UI bugs, the model comments out E2E test commands in the Validation Commands section and adds redundant manual reproduction steps.

### Example of the Problem

Generated output in `input_focus_after_response.md`:

```bash
# 4. Manual reproduction test (in browser):
#    - Navigate to http://localhost:3000
#    - Type "What is the income limit?" and press Enter
#    - Wait for response
#    - Verify cursor is blinking in the input field
#    - Type "abc" immediately - should appear in input without clicking

# 5. E2E test (after creating the test file):
#    /test_e2e random_hex test_e2e .claude/commands/e2e/test_input_focus_after_response.md
```

### Issues

1. **Manual tests are redundant** - The E2E test automates the exact same browser interactions via Playwright. Manual steps duplicate effort and defeat the purpose of E2E testing.

2. **Commented-out commands won't execute** - The template says "Execute every command to validate the bug is fixed with zero regressions." Using `#` prefix turns commands into documentation, violating this requirement.

3. **Hedge indicates sequencing uncertainty** - The parenthetical "(after creating the test file)" shows the model was unsure whether the E2E test file would exist when validation runs.

## Root Cause

The model sees a potential sequencing issue:
- Task 2 creates the E2E test file
- Validation Commands reference that file
- Model hedges by commenting out and adding manual fallback "just in case"

The template doesn't explicitly state that validation runs **after** all tasks are complete.

## Solution

Update `.claude/commands/bug.md` to clarify task sequencing.

### Option A: Add note to Validation Commands section

Change the template's Validation Commands section from:

```md
## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

<list commands...>
```

To:

```md
## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.
These commands assume all Step by Step Tasks above have been completed first.

<list commands...>
```

### Option B: Strengthen Step by Step Tasks header

Change:

```md
## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.
```

To:

```md
## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom. Validation Commands are the final step and depend on all previous tasks being complete.
```

### Option C: Add explicit instruction in the UI bug section

Add to the existing UI bug instructions:

```md
- If the bug affects the UI or user interactions:
  ...existing instructions...
  - The E2E test command in Validation Commands must be uncommented and executable (not manual browser instructions)
```

## Recommended Change

**Option A** is the simplest and most direct fix. It addresses the root cause (sequencing uncertainty) without adding complexity.

## Expected Result

After the fix, generated plans should have:

```bash
# 1. Verify no TypeScript errors
cd frontend && npx tsc --noEmit

# 2. Verify no lint errors
cd frontend && npm run lint

# 3. Start frontend for E2E testing
cd frontend && npm run dev

# 4. Run E2E test to validate focus restoration
/test_e2e random_hex test_e2e .claude/commands/e2e/test_input_focus_after_response.md
```

No manual reproduction steps. No commented-out commands. One executable E2E test as the primary UI validation.
