"""
Quick conversational scenario sanity tests.

These tests run by default (not marked slow) for fast feedback.
For exhaustive testing, run: pytest -m slow

Usage:
    pytest tests/test_conversational_scenarios_quick.py -v
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chatbot import config
from chatbot.chatbot import TexasChildcareChatbot
from evaluation.conversation_evaluator import ConversationEvaluator
from evaluation.multi_turn_judge import MultiTurnJudge

# Scenario directory
SCENARIOS_DIR = project_root / "QUESTIONS" / "conversations" / "scenarios"


class TestConversationalScenariosQuick:
    """Quick sanity check tests for conversational RAG."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Enable conversational mode and initialize components."""
        original = config.CONVERSATIONAL_MODE
        config.CONVERSATIONAL_MODE = True

        self.chatbot = TexasChildcareChatbot()
        self.judge = MultiTurnJudge()
        self.evaluator = ConversationEvaluator(self.chatbot, self.judge)

        yield

        config.CONVERSATIONAL_MODE = original

    def _run_scenario(self, filename: str, min_context_rate: float = 0.90):
        """Helper to run a scenario and assert success."""
        scenario_path = SCENARIOS_DIR / filename
        assert scenario_path.exists(), f"Scenario file not found: {scenario_path}"

        result = self.evaluator.evaluate_conversation(str(scenario_path))

        # Print results for debugging
        print(f"\n--- {result.name} ---")
        for turn in result.turns:
            status = "PASS" if turn.passed else "FAIL"
            print(f"  Turn {turn.turn_number}: {status} (score={turn.composite_score:.1f})")
            if turn.reformulated_query and turn.reformulated_query != turn.user_query:
                print(f"    Reformulated: {turn.reformulated_query[:80]}...")

        print(f"\n  Average Score: {result.average_score:.1f}")
        print(f"  Context Resolution Rate: {result.context_resolution_rate:.1%}")
        print(f"  Passed: {result.conversation_passed}")

        return result

    def test_implicit_context_heavy(self):
        """Test heavy pronoun and implicit reference resolution."""
        result = self._run_scenario("implicit_context_heavy.yaml")

        assert result.conversation_passed, (
            f"Implicit context scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        # Higher bar for context resolution on this test
        assert result.context_resolution_rate >= 0.90, (
            f"Context resolution too low for implicit context test: {result.context_resolution_rate:.1%}"
        )

    def test_eligibility_deep_dive(self):
        """Test multi-step eligibility determination."""
        result = self._run_scenario("eligibility_deep_dive.yaml")

        assert result.conversation_passed, (
            f"Eligibility scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        assert result.context_resolution_rate >= 0.80, (
            f"Context resolution too low: {result.context_resolution_rate:.1%}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
