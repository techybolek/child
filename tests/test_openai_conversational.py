"""
Tests for OpenAI Agent conversational support.

Validates multi-turn conversation functionality with thread-scoped memory.

Usage:
    pytest tests/test_openai_conversational.py -v
    pytest tests/test_openai_conversational.py -v -k "single_turn"  # Run specific test
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler


class TestOpenAIAgentConversational:
    """Tests for OpenAI Agent multi-turn conversation support."""

    @pytest.fixture
    def handler(self):
        """Create handler instance for each test."""
        return OpenAIAgentHandler()

    def test_single_turn_stateless(self, handler):
        """Single query works without thread_id (stateless mode)."""
        result = handler.handle("What is CCS?")

        assert "answer" in result
        assert "sources" in result
        assert "response_type" in result
        assert result["response_type"] in ("information", "error")

        # Should still return thread_id (auto-generated)
        assert "thread_id" in result
        assert "turn_count" in result
        assert result["turn_count"] == 1

    def test_single_turn_with_thread_id(self, handler):
        """Single query with explicit thread_id."""
        thread_id = handler.new_conversation()
        result = handler.handle("What is CCS?", thread_id=thread_id)

        assert result["thread_id"] == thread_id
        assert result["turn_count"] == 1

    def test_multi_turn_history_accumulation(self, handler):
        """Follow-up queries accumulate conversation history."""
        thread_id = handler.new_conversation()

        # Turn 1
        result1 = handler.handle("What is CCS?", thread_id=thread_id)
        assert result1["turn_count"] == 1

        # Turn 2
        result2 = handler.handle("How do I apply for it?", thread_id=thread_id)
        assert result2["turn_count"] == 2

        # Verify history has both turns
        history = handler.get_history(thread_id)
        assert len(history) >= 4  # 2 user + 2 assistant (at minimum)

        # Check user messages are present
        user_messages = [h for h in history if h["role"] == "user"]
        assert len(user_messages) == 2
        assert "CCS" in user_messages[0]["content"]
        assert "apply" in user_messages[1]["content"]

    def test_conversation_isolation(self, handler):
        """Different threads maintain isolated history."""
        thread1 = handler.new_conversation()
        thread2 = handler.new_conversation()

        # Query on thread 1
        handler.handle("What is TANF?", thread_id=thread1)

        # Query on thread 2
        handler.handle("What is CCS?", thread_id=thread2)

        # Histories should be separate
        history1 = handler.get_history(thread1)
        history2 = handler.get_history(thread2)

        # Each should have 1 user turn
        user_msgs_1 = [h for h in history1 if h["role"] == "user"]
        user_msgs_2 = [h for h in history2 if h["role"] == "user"]

        assert len(user_msgs_1) == 1
        assert len(user_msgs_2) == 1

        # Content should be different
        assert "TANF" in user_msgs_1[0]["content"]
        assert "CCS" in user_msgs_2[0]["content"]

    def test_clear_conversation(self, handler):
        """Clearing conversation removes history."""
        thread_id = handler.new_conversation()

        handler.handle("What is CCS?", thread_id=thread_id)
        assert len(handler.get_history(thread_id)) > 0

        handler.clear_conversation(thread_id)
        assert len(handler.get_history(thread_id)) == 0

    def test_new_conversation_returns_unique_ids(self, handler):
        """new_conversation() returns unique thread IDs."""
        ids = [handler.new_conversation() for _ in range(5)]
        assert len(set(ids)) == 5  # All unique

    def test_get_history_nonexistent_thread(self, handler):
        """get_history() returns empty list for unknown thread."""
        history = handler.get_history("nonexistent-thread-id")
        assert history == []

    def test_handle_without_thread_id_generates_new_id(self, handler):
        """Each stateless call generates a new thread_id."""
        result1 = handler.handle("What is CCS?")
        result2 = handler.handle("What is TANF?")

        assert result1["thread_id"] != result2["thread_id"]
        assert result1["turn_count"] == 1
        assert result2["turn_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
