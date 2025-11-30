"""
Multi-turn conversation judge for evaluating chatbot responses in context.
"""

import json
import re
from groq import Groq
from . import config
from .prompts.multi_turn_judge_prompt import MULTI_TURN_JUDGE_PROMPT


class MultiTurnJudge:
    """LLM-as-a-Judge for multi-turn conversations."""

    def __init__(self):
        self.client = Groq(api_key=config.JUDGE_API_KEY)
        self.model = config.JUDGE_MODEL

    def score_turn(
        self,
        query: str,
        reformulated_query: str | None,
        response: str,
        expected_topics: list[str],
        expected_answer_contains: list[str],
        requires_context: bool,
        previous_turns: list
    ) -> dict:
        """Score a single turn with conversation context.

        Args:
            query: Original user query
            reformulated_query: Query after reformulation (if any)
            response: Chatbot response
            expected_topics: Topics that should be covered
            expected_answer_contains: Substrings expected in answer
            requires_context: Whether turn requires context from history
            previous_turns: List of TurnResult objects from previous turns

        Returns:
            dict with accuracy, completeness, coherence scores
        """
        history = self._format_history(previous_turns)

        prompt = MULTI_TURN_JUDGE_PROMPT.format(
            conversation_history=history,
            original_query=query,
            reformulated_query=reformulated_query or query,
            response=response,
            expected_topics=", ".join(expected_topics) if expected_topics else "N/A",
            expected_contains=", ".join(expected_answer_contains) if expected_answer_contains else "N/A",
            requires_context=requires_context
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                seed=config.SEED if hasattr(config, 'SEED') else 42,
                max_tokens=200,
            )

            content = completion.choices[0].message.content
            return self._parse_scores(content)

        except Exception as e:
            print(f"[MultiTurnJudge] ERROR: {type(e).__name__}: {str(e)}")
            return {"accuracy": 3, "completeness": 3, "coherence": 2}

    def _format_history(self, previous_turns) -> str:
        """Format previous turns for prompt injection.

        Args:
            previous_turns: List of TurnResult objects

        Returns:
            Formatted conversation history string
        """
        if not previous_turns:
            return "No previous turns."

        lines = []
        for t in previous_turns:
            lines.append(f"Turn {t.turn_number}:")
            lines.append(f"  User: {t.user_query}")
            # Truncate long responses
            resp = t.response
            if len(resp) > 200:
                resp = resp[:200] + "..."
            lines.append(f"  Assistant: {resp}")
        return "\n".join(lines)

    def _parse_scores(self, content: str) -> dict:
        """Parse JSON scores from LLM response.

        Args:
            content: Raw LLM response

        Returns:
            dict with accuracy, completeness, coherence scores
        """
        if not content:
            return {"accuracy": 3, "completeness": 3, "coherence": 2}

        try:
            # Try to extract JSON from response
            # Handle case where LLM might wrap in markdown code block
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if json_match:
                scores = json.loads(json_match.group())
                # Validate scores
                return {
                    "accuracy": max(1, min(5, scores.get("accuracy", 3))),
                    "completeness": max(1, min(5, scores.get("completeness", 3))),
                    "coherence": max(1, min(3, scores.get("coherence", 2))),
                    "context_resolution_note": scores.get("context_resolution_note")
                }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[MultiTurnJudge] Parse error: {e}")
            print(f"[MultiTurnJudge] Raw content: {content[:200]}")

        # Fallback defaults
        return {"accuracy": 3, "completeness": 3, "coherence": 2}
