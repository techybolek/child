# E2E Test: Clear Chat Functionality

Test that the Clear Chat button works without a confirmation dialog.

## User Story

As a user
I want to clear my chat history instantly
So that I can start fresh without extra confirmation clicks

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the Clear Chat button is NOT visible when there are no messages
4. Enter the query: "hello"
5. Click the Send button
6. Wait for the response to appear
7. Take a screenshot showing the message and Clear Chat button
8. **Verify** the Clear Chat button is now visible
9. Click the Clear Chat button
10. Take a screenshot immediately after clicking
11. **Verify** the chat is cleared (no messages visible)
12. **Verify** NO confirmation dialog appeared (the clear happened immediately)

## Success Criteria
- Clear Chat button is hidden when chat is empty
- Clear Chat button appears after sending a message
- Clicking Clear Chat immediately clears conversation
- NO browser confirmation dialog appears
- Screenshots prove the immediate clearing behavior
