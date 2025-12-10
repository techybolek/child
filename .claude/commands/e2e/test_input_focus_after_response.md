# E2E Test: Input Focus After Response

Test that the query input textarea regains focus after a response completes.

## User Story

As a user
I want the input field to retain focus after the AI responds
So that I can immediately type my next question without clicking

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the query input textbox is present
4. Click into the query input textbox to focus it
5. Enter the query: "What is the income limit?"
6. Take a screenshot of the query input with text
7. Click the Send button
8. **Verify** the loading spinner appears (button shows spinner)
9. Wait for the response to complete (loading spinner disappears, response text appears)
10. Take a screenshot of the completed response
11. **Verify** the query input textarea has focus (document.activeElement should be the textarea)
12. Type "abc" without clicking anywhere
13. **Verify** the characters "abc" appear in the input textarea
14. Take a screenshot showing the typed characters in the focused input

## Success Criteria
- Query input accepts initial text
- Send button triggers execution
- Response displays correctly
- Input textarea has focus after response completes
- Additional characters can be typed immediately without clicking
- Screenshots are taken at each key moment
