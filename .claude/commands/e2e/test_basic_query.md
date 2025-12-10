# E2E Test: Basic Query Execution

Test basic query functionality in the Natural Language SQL Interface application.

## User Story

As a user  
I want to query my data using natural language  
So that I can access information without writing SQL

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Texac Childcare Chatbot"
4. **Verify** core UI elements are present:
   - Query input textbox
   - Send button

5. Enter the query: "whats the eligibility limit for a family of 4"
6. Take a screenshot of the query input
7. Click the Send button
8. **Verify** the response appears and that it answers the question
12. Take a screenshot of the response

## Success Criteria
- Query input accepts text
- Send button triggers execution
- Response displays correctly
- Screenshots are taken
