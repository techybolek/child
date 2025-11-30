"""
Comprehensive conversational scenario tests.

These tests are SEPARATE from test_conversational_rag.py (basic/quick tests).
Run these for thorough validation of conversational RAG across domains.

Usage:
    # Run all scenario tests
    pytest tests/test_conversational_scenarios.py -v

    # Run with debug output
    pytest tests/test_conversational_scenarios.py -v -s

    # Direct execution with formatted output
    python tests/test_conversational_scenarios.py

Scenarios:
    1. PSoC Payment Calculation - numeric reasoning, entity tracking
    2. Attendance Error Resolution - troubleshooting flow
    3. Eligibility Deep Dive - multi-step determination
    4. Absence Policy - policy understanding
    5. Implicit Context Heavy - pronoun/reference stress test
    6. Multi-Child Scenario - accumulating family context
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


class TestConversationalScenarios:
    """Comprehensive scenario tests for conversational RAG."""

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

    def test_psoc_payment_calculation(self):
        """Test PSoC payment calculation across family sizes and income levels."""
        result = self._run_scenario("psoc_payment_calculation.yaml")

        assert result.conversation_passed, (
            f"PSoC scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        assert result.context_resolution_rate >= 0.80, (
            f"Context resolution too low: {result.context_resolution_rate:.1%}"
        )

    def test_attendance_error_resolution(self):
        """Test attendance system troubleshooting flow."""
        result = self._run_scenario("attendance_error_resolution.yaml")

        assert result.conversation_passed, (
            f"Attendance scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        assert result.context_resolution_rate >= 0.80, (
            f"Context resolution too low: {result.context_resolution_rate:.1%}"
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

    def test_absence_policy(self):
        """Test absence policy understanding."""
        result = self._run_scenario("absence_policy.yaml")

        assert result.conversation_passed, (
            f"Absence policy scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        assert result.context_resolution_rate >= 0.80, (
            f"Context resolution too low: {result.context_resolution_rate:.1%}"
        )

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

    def test_multi_child_scenario(self):
        """Test accumulating family context with multiple children."""
        result = self._run_scenario("multi_child_scenario.yaml")

        assert result.conversation_passed, (
            f"Multi-child scenario failed: avg={result.average_score:.1f}, "
            f"context_rate={result.context_resolution_rate:.1%}"
        )
        assert result.context_resolution_rate >= 0.80, (
            f"Context resolution too low: {result.context_resolution_rate:.1%}"
        )


class TestScenarioAggregates:
    """Aggregate tests across all scenarios."""

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

    def test_all_scenarios_average_context_resolution(self):
        """Average context resolution across all scenarios should be >= 90%."""
        scenario_files = list(SCENARIOS_DIR.glob("*.yaml"))
        assert len(scenario_files) >= 6, f"Expected at least 6 scenarios, found {len(scenario_files)}"

        results = []
        for scenario_path in scenario_files:
            result = self.evaluator.evaluate_conversation(str(scenario_path))
            results.append(result)
            print(f"{result.name}: context_rate={result.context_resolution_rate:.1%}, avg_score={result.average_score:.1f}")

        avg_context_rate = sum(r.context_resolution_rate for r in results) / len(results)
        avg_score = sum(r.average_score for r in results) / len(results)

        print(f"\n=== AGGREGATE ===")
        print(f"Average Context Resolution: {avg_context_rate:.1%}")
        print(f"Average Score: {avg_score:.1f}")

        assert avg_context_rate >= 0.90, (
            f"Average context resolution {avg_context_rate:.1%} below 90% target"
        )


def run_all_scenarios():
    """Run all scenarios with formatted output."""
    print("\n" + "=" * 70)
    print("CONVERSATIONAL SCENARIO TESTS")
    print("=" * 70)

    config.CONVERSATIONAL_MODE = True

    chatbot = TexasChildcareChatbot()
    judge = MultiTurnJudge()
    evaluator = ConversationEvaluator(chatbot, judge)

    scenario_files = sorted(SCENARIOS_DIR.glob("*.yaml"))
    print(f"\nFound {len(scenario_files)} scenario files\n")

    all_passed = True
    results = []

    for scenario_path in scenario_files:
        print(f"\n{'─' * 60}")
        print(f"Running: {scenario_path.name}")
        print(f"{'─' * 60}")

        try:
            result = evaluator.evaluate_conversation(str(scenario_path))
            results.append(result)

            for turn in result.turns:
                status = "✓" if turn.passed else "✗"
                print(f"  {status} Turn {turn.turn_number}: {turn.composite_score:.1f}")

            status = "PASS" if result.conversation_passed else "FAIL"
            print(f"\n  Result: {status}")
            print(f"  Average Score: {result.average_score:.1f}")
            print(f"  Context Resolution: {result.context_resolution_rate:.1%}")

            if not result.conversation_passed:
                all_passed = False

        except Exception as e:
            print(f"  ERROR: {e}")
            all_passed = False

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if results:
        avg_score = sum(r.average_score for r in results) / len(results)
        avg_context = sum(r.context_resolution_rate for r in results) / len(results)
        passed_count = sum(1 for r in results if r.conversation_passed)

        print(f"Scenarios: {passed_count}/{len(results)} passed")
        print(f"Average Score: {avg_score:.1f}")
        print(f"Average Context Resolution: {avg_context:.1%}")

    if all_passed:
        print("\n✓ ALL SCENARIOS PASSED")
        return 0
    else:
        print("\n✗ SOME SCENARIOS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_scenarios())
