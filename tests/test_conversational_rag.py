"""
Phase-gated tests for conversational RAG implementation.

Each TestMilestone class gates a phase - all tests must pass before proceeding.

Milestones:
    1. State + Memory     - Thread isolation, memory persistence
    2. Query Reformulation - Pronoun resolution, context expansion
    3. Testing Framework   - YAML parsing, evaluator, judge

Usage:
    # Direct execution (recommended) - stops on first failure, clean output
    python tests/test_conversational_rag.py

    # pytest with stop-on-failure
    pytest tests/test_conversational_rag.py -x -v

    # pytest run all (verbose output)
    pytest tests/test_conversational_rag.py -v

    # Single milestone only
    pytest tests/test_conversational_rag.py::TestMilestone1 -v
    pytest tests/test_conversational_rag.py::TestMilestone2 -v
    pytest tests/test_conversational_rag.py::TestMilestone3 -v

    # Single test
    pytest tests/test_conversational_rag.py::TestMilestone2::test_pronoun_resolution -v

Output:
    - On success: single checkmark line per test
    - On failure: clear banner + last 15 lines of debug output
"""

import pytest
import sys
import io
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def capture_output():
    """Capture stdout/stderr during test, show last 15 lines on failure only."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        yield
    except Exception:
        # On failure, restore streams and print last 15 lines
        output = sys.stdout.getvalue()
        sys.stdout, sys.stderr = old_stdout, old_stderr
        if output:
            lines = output.strip().split('\n')
            if len(lines) > 15:
                print(f"\n--- Last 15 of {len(lines)} lines ---")
                print('\n'.join(lines[-15:]))
            else:
                print("\n--- Captured Output ---")
                print(output)
            print("--- End Output ---")
        raise
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chatbot import config


class TestMilestone1:
    """Gate: State + Memory

    Tests for basic conversational memory functionality.
    All tests must pass before proceeding to Milestone 2.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Enable conversational mode for tests."""
        original = config.CONVERSATIONAL_MODE
        config.CONVERSATIONAL_MODE = True
        yield
        config.CONVERSATIONAL_MODE = original

    def test_memory_persistence(self):
        """Memory persists across turns within same thread."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        thread_id = bot.new_conversation()

        r1 = bot.ask("What is CCS?", thread_id=thread_id)
        assert r1["turn_count"] == 1, f"Expected turn_count=1, got {r1['turn_count']}"
        assert r1["thread_id"] == thread_id

        r2 = bot.ask("Tell me more about eligibility", thread_id=thread_id)
        assert r2["turn_count"] == 2, f"Expected turn_count=2, got {r2['turn_count']}"
        assert r2["thread_id"] == thread_id

    def test_thread_isolation(self):
        """Different threads have isolated memory."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()

        r1 = bot.ask("What is CCS?", thread_id="thread-A")
        r2 = bot.ask("What is CCMS?", thread_id="thread-B")

        history_a = bot.get_history("thread-A")
        history_b = bot.get_history("thread-B")

        assert len(history_a) == 2, f"Expected 2 messages in thread-A, got {len(history_a)}"
        assert len(history_b) == 2, f"Expected 2 messages in thread-B, got {len(history_b)}"

        # Verify content is isolated
        assert "CCS" in history_a[0]["content"], "Thread A should contain CCS query"
        assert "CCMS" in history_b[0]["content"], "Thread B should contain CCMS query"

    def test_stateless_mode_unchanged(self):
        """CONVERSATIONAL_MODE=false preserves original behavior."""
        from chatbot import TexasChildcareChatbot

        # Temporarily disable conversational mode
        config.CONVERSATIONAL_MODE = False

        bot = TexasChildcareChatbot()
        result = bot.ask("What is CCS?")

        # Should not have thread_id or turn_count
        assert "thread_id" not in result or result.get("thread_id") is None
        assert "turn_count" not in result or result.get("turn_count") is None

        # Should still have answer
        assert "answer" in result
        assert len(result["answer"]) > 10


def run_milestone1_tests():
    """Run Milestone 1 tests with formatted output. Stops on first failure."""
    print("\n" + "=" * 60)
    print("MILESTONE 1: State + Memory Tests")
    print("=" * 60)

    tests = [
        ("test_memory_persistence", "Memory persists across turns"),
        ("test_thread_isolation", "Thread isolation"),
        ("test_stateless_mode_unchanged", "Stateless mode unchanged"),
    ]

    # Enable conversational mode
    original = config.CONVERSATIONAL_MODE
    config.CONVERSATIONAL_MODE = True

    passed = 0

    try:
        for test_name, description in tests:
            try:
                test_class = TestMilestone1()
                with capture_output():
                    if test_name == "test_memory_persistence":
                        test_class.test_memory_persistence()
                    elif test_name == "test_thread_isolation":
                        test_class.test_thread_isolation()
                    elif test_name == "test_stateless_mode_unchanged":
                        test_class.test_stateless_mode_unchanged()

                print(f"  ✓ {description}")
                passed += 1

            except Exception as e:
                print(f"\n{'='*60}")
                print(f"  ✗ FAILED: {description}")
                print(f"{'='*60}")
                print(f"    {type(e).__name__}: {e}")
                print(f"{'='*60}")
                return False  # Stop on first failure

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, 0 failed")
    print("=" * 60)

    return True


class TestMilestone2:
    """Gate: Query Reformulation

    Tests for context-aware query reformulation.
    All tests must pass before proceeding to Milestone 3.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Enable conversational mode for tests."""
        original = config.CONVERSATIONAL_MODE
        config.CONVERSATIONAL_MODE = True
        yield
        config.CONVERSATIONAL_MODE = original

    def test_pronoun_resolution(self):
        """Pronouns are resolved using conversation context."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        thread_id = bot.new_conversation()

        # First turn: establish context
        r1 = bot.ask("What is CCS?", thread_id=thread_id)
        assert "answer" in r1

        # Second turn: use pronoun "it"
        r2 = bot.ask("How do I apply for it?", thread_id=thread_id, debug=True)
        assert "answer" in r2

        # Reformulated query should mention CCS explicitly
        reformulated = r2.get("reformulated_query", "")
        print(f"Original: How do I apply for it?")
        print(f"Reformulated: {reformulated}")

        # Should expand "it" to reference CCS
        assert "CCS" in reformulated or "Child Care" in reformulated, \
            f"Expected CCS in reformulated query, got: {reformulated}"

    def test_implicit_context_resolution(self):
        """Implicit context references are expanded."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        thread_id = bot.new_conversation()

        # First turn: ask about family of 3
        r1 = bot.ask("What is the income limit for a family of 3?", thread_id=thread_id)
        assert "answer" in r1

        # Second turn: "what about 4" implicitly refers to family size
        r2 = bot.ask("What about for 4?", thread_id=thread_id, debug=True)
        assert "answer" in r2

        reformulated = r2.get("reformulated_query", "")
        print(f"Original: What about for 4?")
        print(f"Reformulated: {reformulated}")

        # Should expand to include "income limit" and "family of 4" (or "four")
        reformulated_lower = reformulated.lower()
        assert ("4" in reformulated_lower or "four" in reformulated_lower), \
            f"Expected '4' or 'four' in reformulated query, got: {reformulated}"
        assert ("income" in reformulated_lower or "family" in reformulated_lower or "limit" in reformulated_lower), \
            f"Expected context from previous turn, got: {reformulated}"

    def test_standalone_query_passthrough(self):
        """Standalone queries pass through unchanged."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        thread_id = bot.new_conversation()

        # First turn
        r1 = bot.ask("What is CCS?", thread_id=thread_id)

        # Second turn: completely standalone question
        standalone_query = "What are the Texas Rising Star quality standards?"
        r2 = bot.ask(standalone_query, thread_id=thread_id, debug=True)

        reformulated = r2.get("reformulated_query", "")
        print(f"Original: {standalone_query}")
        print(f"Reformulated: {reformulated}")

        # Standalone query should remain relatively unchanged
        # (might have minor rewording but core meaning preserved)
        assert "Texas Rising Star" in reformulated or "quality" in reformulated.lower(), \
            f"Standalone query was incorrectly modified: {reformulated}"

    def test_first_turn_no_reformulation(self):
        """First turn skips reformulation (no history)."""
        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        thread_id = bot.new_conversation()

        query = "What are the income limits for childcare assistance?"
        r1 = bot.ask(query, thread_id=thread_id, debug=True)

        reformulated = r1.get("reformulated_query", "")
        print(f"First turn query: {query}")
        print(f"Reformulated: {reformulated}")

        # First turn should use original query (no history to reformulate from)
        assert reformulated == query or reformulated == "", \
            f"First turn should not reformulate, got: {reformulated}"


def run_milestone2_tests():
    """Run Milestone 2 tests with formatted output. Stops on first failure."""
    print("\n" + "=" * 60)
    print("MILESTONE 2: Query Reformulation Tests")
    print("=" * 60)

    tests = [
        ("test_pronoun_resolution", "Pronoun resolution (it → CCS)"),
        ("test_implicit_context_resolution", "Implicit context (what about 4?)"),
        ("test_standalone_query_passthrough", "Standalone query passthrough"),
        ("test_first_turn_no_reformulation", "First turn skips reformulation"),
    ]

    # Enable conversational mode
    original = config.CONVERSATIONAL_MODE
    config.CONVERSATIONAL_MODE = True

    passed = 0

    try:
        for test_name, description in tests:
            try:
                test_class = TestMilestone2()
                with capture_output():
                    if test_name == "test_pronoun_resolution":
                        test_class.test_pronoun_resolution()
                    elif test_name == "test_implicit_context_resolution":
                        test_class.test_implicit_context_resolution()
                    elif test_name == "test_standalone_query_passthrough":
                        test_class.test_standalone_query_passthrough()
                    elif test_name == "test_first_turn_no_reformulation":
                        test_class.test_first_turn_no_reformulation()

                print(f"  ✓ {description}")
                passed += 1

            except Exception as e:
                print(f"\n{'='*60}")
                print(f"  ✗ FAILED: {description}")
                print(f"{'='*60}")
                print(f"    {type(e).__name__}: {e}")
                print(f"{'='*60}")
                return False  # Stop on first failure

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, 0 failed")
    print("=" * 60)

    return True


class TestMilestone3:
    """Gate: Testing Framework

    Tests for the multi-turn conversation testing framework.
    All tests must pass before proceeding to Milestone 4.

    Milestone 3 Checklist:
    - YAML parsing works
    - Evaluator runs without error
    - Context metric calculated
    - Judge scores turns correctly
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Enable conversational mode for tests."""
        original = config.CONVERSATIONAL_MODE
        config.CONVERSATIONAL_MODE = True
        yield
        config.CONVERSATIONAL_MODE = original

    def test_yaml_parsing(self):
        """YAML conversation files parse correctly."""
        import yaml

        conv_file = Path("QUESTIONS/conversations/ccs_eligibility_conv.yaml")
        assert conv_file.exists(), f"Conversation file not found: {conv_file}"

        spec = yaml.safe_load(conv_file.read_text())

        assert "name" in spec, "Missing 'name' field"
        assert "conversation" in spec, "Missing 'conversation' field"
        assert len(spec["conversation"]) >= 2, "Need at least 2 turns"
        assert spec["conversation"][0]["turn"] == 1, "First turn should be turn 1"

        # Verify turn structure
        for turn in spec["conversation"]:
            assert "turn" in turn, "Turn missing 'turn' number"
            assert "user" in turn, "Turn missing 'user' query"

    def test_evaluator_runs(self):
        """ConversationEvaluator executes without error."""
        from chatbot import TexasChildcareChatbot
        from evaluation.conversation_evaluator import ConversationEvaluator
        from evaluation.multi_turn_judge import MultiTurnJudge

        bot = TexasChildcareChatbot()
        judge = MultiTurnJudge()
        evaluator = ConversationEvaluator(bot, judge)

        result = evaluator.evaluate_conversation(
            "QUESTIONS/conversations/ccs_eligibility_conv.yaml"
        )

        assert result.name == "CCS Eligibility Multi-Turn", f"Wrong name: {result.name}"
        assert len(result.turns) >= 1, "Should have at least 1 turn result"
        assert result.average_score >= 0, "Average score should be non-negative"

    def test_context_metric_calculated(self):
        """Context resolution rate is calculated."""
        from chatbot import TexasChildcareChatbot
        from evaluation.conversation_evaluator import ConversationEvaluator
        from evaluation.multi_turn_judge import MultiTurnJudge

        bot = TexasChildcareChatbot()
        judge = MultiTurnJudge()
        evaluator = ConversationEvaluator(bot, judge)

        result = evaluator.evaluate_conversation(
            "QUESTIONS/conversations/ccs_eligibility_conv.yaml"
        )

        assert 0 <= result.context_resolution_rate <= 1.0, \
            f"Context rate should be 0-1, got: {result.context_resolution_rate}"

    def test_judge_scores_turn(self):
        """MultiTurnJudge returns valid scores."""
        from evaluation.multi_turn_judge import MultiTurnJudge

        judge = MultiTurnJudge()
        scores = judge.score_turn(
            query="What about for a family of 4?",
            reformulated_query="What are the income limits for a family of 4 for CCS?",
            response="For a family of 4, the income limit is 85% of SMI.",
            expected_topics=["income", "family"],
            expected_answer_contains=["family of 4"],
            requires_context=True,
            previous_turns=[]
        )

        assert "accuracy" in scores, "Missing accuracy score"
        assert "completeness" in scores, "Missing completeness score"
        assert "coherence" in scores, "Missing coherence score"
        assert 1 <= scores["accuracy"] <= 5, f"Accuracy out of range: {scores['accuracy']}"
        assert 1 <= scores["completeness"] <= 5, f"Completeness out of range: {scores['completeness']}"
        assert 1 <= scores["coherence"] <= 3, f"Coherence out of range: {scores['coherence']}"


def run_milestone3_tests():
    """Run Milestone 3 tests with formatted output. Stops on first failure."""
    print("\n" + "=" * 60)
    print("MILESTONE 3: Testing Framework Tests")
    print("=" * 60)

    tests = [
        ("test_yaml_parsing", "YAML conversation parsing"),
        ("test_evaluator_runs", "Evaluator executes"),
        ("test_context_metric_calculated", "Context metric calculated"),
        ("test_judge_scores_turn", "Judge scores turn"),
    ]

    # Enable conversational mode
    original = config.CONVERSATIONAL_MODE
    config.CONVERSATIONAL_MODE = True

    passed = 0

    try:
        for test_name, description in tests:
            try:
                test_class = TestMilestone3()
                with capture_output():
                    if test_name == "test_yaml_parsing":
                        test_class.test_yaml_parsing()
                    elif test_name == "test_evaluator_runs":
                        test_class.test_evaluator_runs()
                    elif test_name == "test_context_metric_calculated":
                        test_class.test_context_metric_calculated()
                    elif test_name == "test_judge_scores_turn":
                        test_class.test_judge_scores_turn()

                print(f"  ✓ {description}")
                passed += 1

            except Exception as e:
                print(f"\n{'='*60}")
                print(f"  ✗ FAILED: {description}")
                print(f"{'='*60}")
                print(f"    {type(e).__name__}: {e}")
                print(f"{'='*60}")
                return False  # Stop on first failure

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, 0 failed")
    print("=" * 60)

    return True


class TestMilestone4:
    """Gate: Full E2E Integration

    Tests for complete conversational RAG pipeline.
    All tests must pass to complete the conversational RAG implementation.

    Milestone 4 Checklist:
    - Full conversation evaluation runs
    - Context resolution meets 90% target
    - Stateless evaluation still works
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Enable conversational mode for tests."""
        original = config.CONVERSATIONAL_MODE
        config.CONVERSATIONAL_MODE = True
        yield
        config.CONVERSATIONAL_MODE = original

    def test_full_conversation_evaluation(self):
        """Run all conversation YAML files and verify no critical failures."""
        from chatbot import TexasChildcareChatbot
        from evaluation.conversation_evaluator import ConversationEvaluator
        from evaluation.multi_turn_judge import MultiTurnJudge

        bot = TexasChildcareChatbot()
        judge = MultiTurnJudge()
        evaluator = ConversationEvaluator(bot, judge)

        conv_dir = Path("QUESTIONS/conversations")
        conv_files = list(conv_dir.glob("*.yaml"))

        assert len(conv_files) >= 3, f"Expected at least 3 conversation files, got {len(conv_files)}"

        results = []
        for conv_file in conv_files:
            result = evaluator.evaluate_conversation(str(conv_file))
            results.append(result)
            print(f"  {conv_file.name}: avg={result.average_score:.1f}, context={result.context_resolution_rate:.1%}")

        # At least one conversation should complete
        assert len(results) == len(conv_files), "Not all conversations evaluated"

    def test_context_resolution_meets_target(self):
        """Context resolution rate >= 90% across all conversations."""
        from chatbot import TexasChildcareChatbot
        from evaluation.conversation_evaluator import ConversationEvaluator
        from evaluation.multi_turn_judge import MultiTurnJudge

        bot = TexasChildcareChatbot()
        judge = MultiTurnJudge()
        evaluator = ConversationEvaluator(bot, judge)

        conv_dir = Path("QUESTIONS/conversations")
        conv_files = list(conv_dir.glob("*.yaml"))

        total_context_rate = 0
        count = 0

        for conv_file in conv_files:
            result = evaluator.evaluate_conversation(str(conv_file))
            total_context_rate += result.context_resolution_rate
            count += 1

        avg_context_rate = total_context_rate / count if count > 0 else 0
        print(f"Average context resolution rate: {avg_context_rate:.1%}")

        assert avg_context_rate >= 0.90, \
            f"Context resolution rate {avg_context_rate:.1%} below 90% target"

    def test_stateless_evaluation_still_works(self):
        """Existing single-turn evaluation framework unchanged."""
        # Temporarily disable conversational mode
        config.CONVERSATIONAL_MODE = False

        from chatbot import TexasChildcareChatbot

        bot = TexasChildcareChatbot()
        result = bot.ask("What is CCS?")

        # Should work in stateless mode
        assert "answer" in result, "Missing answer in stateless mode"
        assert len(result["answer"]) > 10, "Answer too short"

        # Should not have conversational fields
        assert "thread_id" not in result or result.get("thread_id") is None, \
            "Stateless mode should not have thread_id"


def run_milestone4_tests():
    """Run Milestone 4 tests with formatted output. Stops on first failure."""
    print("\n" + "=" * 60)
    print("MILESTONE 4: Full E2E Integration Tests")
    print("=" * 60)

    tests = [
        ("test_full_conversation_evaluation", "Full conversation evaluation"),
        ("test_context_resolution_meets_target", "Context resolution >= 90%"),
        ("test_stateless_evaluation_still_works", "Stateless mode unchanged"),
    ]

    # Enable conversational mode
    original = config.CONVERSATIONAL_MODE
    config.CONVERSATIONAL_MODE = True

    passed = 0

    try:
        for test_name, description in tests:
            try:
                test_class = TestMilestone4()
                with capture_output():
                    if test_name == "test_full_conversation_evaluation":
                        test_class.test_full_conversation_evaluation()
                    elif test_name == "test_context_resolution_meets_target":
                        test_class.test_context_resolution_meets_target()
                    elif test_name == "test_stateless_evaluation_still_works":
                        test_class.test_stateless_evaluation_still_works()

                print(f"  ✓ {description}")
                passed += 1

            except Exception as e:
                print(f"\n{'='*60}")
                print(f"  ✗ FAILED: {description}")
                print(f"{'='*60}")
                print(f"    {type(e).__name__}: {e}")
                print(f"{'='*60}")
                return False  # Stop on first failure

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, 0 failed")
    print("=" * 60)

    return True


def run_all_tests():
    """Run all milestone tests with formatted output."""
    print("\n" + "=" * 70)
    print("CONVERSATIONAL RAG TEST SUITE")
    print("=" * 70)

    all_passed = True

    # Milestone 1
    if not run_milestone1_tests():
        all_passed = False
        print("\n*** MILESTONE 1 FAILED - Fix before proceeding ***\n")
        return False

    # Milestone 2
    if not run_milestone2_tests():
        all_passed = False
        print("\n*** MILESTONE 2 FAILED - Fix before proceeding ***\n")
        return False

    # Milestone 3
    if not run_milestone3_tests():
        all_passed = False
        print("\n*** MILESTONE 3 FAILED - Fix before proceeding ***\n")
        return False

    # Milestone 4
    if not run_milestone4_tests():
        all_passed = False
        print("\n*** MILESTONE 4 FAILED - Fix before proceeding ***\n")
        return False

    if all_passed:
        print("\n*** ALL MILESTONES PASSED ***\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
