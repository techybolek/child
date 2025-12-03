"""
Conversational RAG regression tests.

Tests core memory and query reformulation functionality.

Usage:
    pytest tests/test_conversational_rag.py -v
    pytest tests/test_conversational_rag.py::TestConversationalMemory -v
    pytest tests/test_conversational_rag.py::TestQueryReformulation::test_pronoun_resolution -v

    # Direct execution
    python tests/test_conversational_rag.py
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chatbot import config


class TestConversationalMemory:
    """Tests for conversation memory and thread isolation."""

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


class TestQueryReformulation:
    """Tests for context-aware query reformulation."""

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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
