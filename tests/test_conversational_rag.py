"""
Phase-gated tests for conversational RAG implementation.

Each TestMilestone class gates a phase - all tests must pass before proceeding.

Usage:
    pytest tests/test_conversational_rag.py -v                     # All tests
    pytest tests/test_conversational_rag.py::TestMilestone1 -v     # Phase 1 only
    python tests/test_conversational_rag.py                        # Direct execution
"""

import pytest
import sys
from pathlib import Path

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
    """Run Milestone 1 tests with formatted output."""
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
    failed = 0

    try:
        from chatbot import TexasChildcareChatbot

        for test_name, description in tests:
            try:
                test_class = TestMilestone1()

                if test_name == "test_memory_persistence":
                    test_class.test_memory_persistence()
                elif test_name == "test_thread_isolation":
                    test_class.test_thread_isolation()
                elif test_name == "test_stateless_mode_unchanged":
                    test_class.test_stateless_mode_unchanged()

                print(f"  ✓ {description}")
                passed += 1

            except Exception as e:
                print(f"  ✗ {description}")
                print(f"    Error: {e}")
                failed += 1

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


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

        # Should expand to include "income limit" and "family of 4"
        reformulated_lower = reformulated.lower()
        assert "4" in reformulated_lower, f"Expected '4' in reformulated query"
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
    """Run Milestone 2 tests with formatted output."""
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
    failed = 0

    try:
        from chatbot import TexasChildcareChatbot

        for test_name, description in tests:
            try:
                test_class = TestMilestone2()

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

            except AssertionError as e:
                print(f"  ✗ {description}")
                print(f"    Assertion: {e}")
                failed += 1

            except Exception as e:
                print(f"  ✗ {description}")
                print(f"    Error: {type(e).__name__}: {e}")
                failed += 1

    finally:
        config.CONVERSATIONAL_MODE = original

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


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

    if all_passed:
        print("\n*** ALL MILESTONES PASSED ***\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
