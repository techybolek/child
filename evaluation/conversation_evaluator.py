"""
Conversation evaluator for multi-turn chatbot testing.
"""

from dataclasses import dataclass
from pathlib import Path
import yaml

from chatbot.chatbot import TexasChildcareChatbot
from .multi_turn_judge import MultiTurnJudge


@dataclass
class TurnResult:
    """Result for a single conversation turn."""
    turn_number: int
    user_query: str
    reformulated_query: str | None
    response: str
    expected_topics: list[str]

    # Scores
    factual_accuracy: float
    completeness: float
    context_resolution: float
    coherence: float
    composite_score: float

    passed: bool


@dataclass
class ConversationResult:
    """Aggregate result for a full conversation."""
    name: str
    thread_id: str
    turns: list[TurnResult]

    # Aggregate metrics
    average_score: float
    context_resolution_rate: float
    all_turns_passed: bool
    conversation_passed: bool


class ConversationEvaluator:
    """Evaluates multi-turn conversations against expected behavior."""

    def __init__(self, chatbot: TexasChildcareChatbot, judge: MultiTurnJudge):
        """Initialize evaluator.

        Args:
            chatbot: Configured chatbot instance
            judge: Multi-turn judge for scoring
        """
        self.chatbot = chatbot
        self.judge = judge

    def evaluate_conversation(self, conv_file: str) -> ConversationResult:
        """Run and evaluate a full conversation.

        Args:
            conv_file: Path to YAML conversation file

        Returns:
            ConversationResult with turn-by-turn and aggregate scores
        """
        conv_spec = yaml.safe_load(open(conv_file))

        thread_id = self.chatbot.new_conversation()
        turn_results = []

        for turn_spec in conv_spec["conversation"]:
            result = self._evaluate_turn(
                thread_id=thread_id,
                turn_spec=turn_spec,
                previous_turns=turn_results
            )
            turn_results.append(result)

            # Stop on fail if configured
            if not result.passed and conv_spec.get("stop_on_fail", True):
                break

        return self._aggregate_results(
            conv_spec["name"],
            thread_id,
            turn_results,
            conv_spec
        )

    def _evaluate_turn(
        self,
        thread_id: str,
        turn_spec: dict,
        previous_turns: list[TurnResult]
    ) -> TurnResult:
        """Evaluate a single turn.

        Args:
            thread_id: Conversation thread ID
            turn_spec: Turn specification from YAML
            previous_turns: Previous turn results

        Returns:
            TurnResult with scores
        """
        # Get chatbot response
        response = self.chatbot.ask(
            question=turn_spec["user"],
            thread_id=thread_id,
            debug=True
        )

        # Score with judge
        scores = self.judge.score_turn(
            query=turn_spec["user"],
            reformulated_query=response.get("reformulated_query"),
            response=response["answer"],
            expected_topics=turn_spec.get("expected_topics", []),
            expected_answer_contains=turn_spec.get("expected_answer_contains", []),
            requires_context=turn_spec.get("requires_context", False),
            previous_turns=previous_turns
        )

        # Calculate context resolution score
        context_score = self._check_context_resolution(
            turn_spec, response, previous_turns
        ) if turn_spec.get("requires_context") else 1.0

        # Calculate composite score
        composite = self._calculate_composite(scores, context_score)

        return TurnResult(
            turn_number=turn_spec["turn"],
            user_query=turn_spec["user"],
            reformulated_query=response.get("reformulated_query"),
            response=response["answer"],
            expected_topics=turn_spec.get("expected_topics", []),
            factual_accuracy=scores["accuracy"],
            completeness=scores["completeness"],
            context_resolution=context_score,
            coherence=scores["coherence"],
            composite_score=composite,
            passed=composite >= turn_spec.get("min_score", 70)
        )

    def _check_context_resolution(
        self,
        turn_spec: dict,
        response: dict,
        previous_turns: list[TurnResult]
    ) -> float:
        """Check if context-dependent references were resolved.

        Args:
            turn_spec: Turn specification
            response: Chatbot response dict
            previous_turns: Previous turns for context

        Returns:
            Score from 0.0 to 1.0
        """
        reformulated = response.get("reformulated_query", "")
        original = turn_spec["user"]

        # Context markers that indicate implicit references
        context_markers = ["it", "they", "this", "that", "what about", "how about", "and if"]
        has_markers = any(m in original.lower() for m in context_markers)

        if not has_markers:
            return 1.0  # No context resolution needed

        # Reformulated should be longer/more specific than original
        if len(reformulated) <= len(original):
            return 0.0  # Failed to expand

        # Check if key terms from previous response are incorporated
        if previous_turns:
            last_response = previous_turns[-1].response.lower()
            # Extract likely key terms (simple heuristic)
            key_terms = self._extract_key_terms(last_response)
            if key_terms:
                matched = sum(1 for t in key_terms if t in reformulated.lower())
                return min(1.0, matched / len(key_terms))

        return 0.8  # Partial credit for expansion

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract likely key terms from text for context checking.

        Args:
            text: Text to extract terms from

        Returns:
            List of key terms
        """
        # Simple extraction: words that look like key terms
        # (not stop words, longer than 3 chars)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for",
                      "in", "on", "at", "by", "with", "from", "of", "and", "or",
                      "that", "this", "it", "you", "your", "can", "will", "would",
                      "should", "could", "may", "might", "must", "have", "has",
                      "been", "being", "be", "as", "if", "than", "then", "so",
                      "such", "when", "where", "which", "who", "whom", "what"}

        words = text.split()
        key_terms = [
            w.strip(".,!?;:'\"()[]{}") for w in words
            if len(w) > 3 and w.lower() not in stop_words
        ]

        # Return top 5 unique terms
        seen = set()
        result = []
        for t in key_terms:
            if t.lower() not in seen:
                seen.add(t.lower())
                result.append(t.lower())
                if len(result) >= 5:
                    break
        return result

    def _calculate_composite(self, scores: dict, context_score: float) -> float:
        """Calculate weighted composite score (0-100 scale).

        Args:
            scores: Dict with accuracy (1-5), completeness (1-5), coherence (1-3)
            context_score: Context resolution score (0-1)

        Returns:
            Composite score (0-100)
        """
        # Normalize each to 0-100, then weight
        accuracy_norm = (scores["accuracy"] / 5) * 100
        completeness_norm = (scores["completeness"] / 5) * 100
        context_norm = context_score * 100
        coherence_norm = (scores["coherence"] / 3) * 100

        return (
            accuracy_norm * 0.45 +
            completeness_norm * 0.30 +
            context_norm * 0.15 +
            coherence_norm * 0.10
        )

    def _aggregate_results(
        self,
        name: str,
        thread_id: str,
        turns: list[TurnResult],
        spec: dict
    ) -> ConversationResult:
        """Aggregate turn results into conversation result.

        Args:
            name: Conversation name
            thread_id: Thread ID used
            turns: List of turn results
            spec: Original conversation spec

        Returns:
            ConversationResult with aggregate metrics
        """
        if not turns:
            return ConversationResult(
                name=name,
                thread_id=thread_id,
                turns=[],
                average_score=0,
                context_resolution_rate=0,
                all_turns_passed=False,
                conversation_passed=False
            )

        # Calculate average score
        avg_score = sum(t.composite_score for t in turns) / len(turns)

        # Calculate context resolution rate
        context_turns = [
            t for t in turns
            if any(m in t.user_query.lower() for m in
                   ["it", "they", "what about", "how about", "and if"])
        ]
        if context_turns:
            context_rate = sum(
                1 for t in context_turns if t.context_resolution >= 0.8
            ) / len(context_turns)
        else:
            context_rate = 1.0  # No context-dependent turns

        # Check success criteria
        criteria = spec.get("success_criteria", {})
        all_passed = all(t.passed for t in turns)

        passed = (
            avg_score >= criteria.get("min_average_score", 70) and
            (not criteria.get("all_turns_pass", False) or all_passed) and
            context_rate >= criteria.get("context_resolution_rate", 0.9)
        )

        return ConversationResult(
            name=name,
            thread_id=thread_id,
            turns=turns,
            average_score=avg_score,
            context_resolution_rate=context_rate,
            all_turns_passed=all_passed,
            conversation_passed=passed
        )
