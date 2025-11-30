"""
Multi-turn conversation judge prompt for evaluating chatbot responses.
"""

MULTI_TURN_JUDGE_PROMPT = """You are evaluating a chatbot response in a multi-turn conversation about Texas childcare assistance.

## Conversation History
{conversation_history}

## Current Turn
Original Query: {original_query}
Reformulated Query: {reformulated_query}
Response: {response}

## Expectations
Expected Topics: {expected_topics}
Expected to Contain: {expected_contains}
Requires Context Resolution: {requires_context}

## Scoring Criteria

1. **Accuracy** (1-5): Is the information factually correct for Texas childcare programs?
   - 5: All facts are accurate and properly sourced
   - 4: Minor inaccuracies that don't affect the main answer
   - 3: Some inaccuracies present
   - 2: Significant factual errors
   - 1: Mostly incorrect or misleading

2. **Completeness** (1-5): Does the response fully address the question?
   - 5: Comprehensive answer covering all aspects
   - 4: Covers main points, minor details missing
   - 3: Addresses the question but incomplete
   - 2: Partially addresses the question
   - 1: Fails to address the question

3. **Coherence** (1-3): Is the response clear and well-structured?
   - 3: Clear, logical, easy to follow
   - 2: Understandable but could be clearer
   - 1: Confusing or poorly organized

If requires_context=True, also evaluate whether the response correctly interpreted references from previous turns (pronouns like "it", "they", implicit context like "what about").

## Output Format
Return ONLY a JSON object with no additional text:
{{
    "accuracy": <1-5>,
    "completeness": <1-5>,
    "coherence": <1-3>,
    "context_resolution_note": "<brief explanation if context was required, otherwise null>"
}}
"""
