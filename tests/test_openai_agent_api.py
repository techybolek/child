"""
API tests for OpenAI Agent mode.

Tests the OpenAI Agent mode endpoints:
- GET /api/models/openai-agent
- POST /api/chat with mode='openai_agent'
"""

import pytest
import requests
import uuid
import os

RELIABLE_QUESTION = "What is CCS?"


def openai_configured():
    """Check if OpenAI API key is configured."""
    return bool(os.getenv('OPENAI_API_KEY'))


# Skip all tests in this module if OpenAI not configured
pytestmark = pytest.mark.skipif(
    not openai_configured(),
    reason="OPENAI_API_KEY not configured"
)


class TestOpenAIAgentModelsEndpoint:
    """Tests for /api/models/openai-agent endpoint."""

    def test_returns_200_with_structure(self, backend_server):
        """Endpoint should return 200 with models list and default."""
        r = requests.get(f"{backend_server}/api/models/openai-agent")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert "default" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_returns_expected_models(self, backend_server):
        """Should include expected model IDs."""
        r = requests.get(f"{backend_server}/api/models/openai-agent")
        assert r.status_code == 200
        data = r.json()
        model_ids = [m["id"] for m in data["models"]]
        # Verify some expected models are present
        assert "gpt-4o-mini" in model_ids
        assert "gpt-5-nano" in model_ids

    def test_models_have_id_and_name(self, backend_server):
        """Each model should have id and name fields."""
        r = requests.get(f"{backend_server}/api/models/openai-agent")
        assert r.status_code == 200
        data = r.json()
        for model in data["models"]:
            assert "id" in model
            assert "name" in model


class TestOpenAIAgentChatEndpoint:
    """Tests for /api/chat with mode='openai_agent'."""

    def test_returns_answer_and_sources(self, backend_server):
        """Response should include answer, sources, and metadata."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": RELIABLE_QUESTION,
                "mode": "openai_agent"
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert "timestamp" in data
        assert "processing_time" in data
        assert data["processing_time"] >= 0
        assert len(data["answer"]) > 10  # Non-empty answer

class TestOpenAIAgentConversational:
    """Tests for OpenAI Agent multi-turn conversation."""

    def test_conversation_preserves_history(self, backend_server):
        """Multi-turn conversation should preserve context.

        Turn 1: Ask about CCS
        Turn 2: Follow-up "How do I apply for it?" should resolve "it" to CCS
        """
        session_id = f"openai-conv-test-{uuid.uuid4()}"

        # Turn 1: Ask about CCS
        r1 = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "What is CCS?",
                "mode": "openai_agent",
                "session_id": session_id
            }
        )
        assert r1.status_code == 200
        data1 = r1.json()
        assert "answer" in data1
        assert len(data1["answer"]) > 50, "First response should be substantial"

        # Turn 2: Follow-up with pronoun reference
        r2 = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "How do I apply for it?",
                "mode": "openai_agent",
                "session_id": session_id
            }
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert "answer" in data2
        assert len(data2["answer"]) > 50, "Follow-up should be substantial"

        # The response should relate to CCS application, not be a generic "what is it?" response
        answer_lower = data2["answer"].lower()
        # Should mention application process, workforce, or CCS-related terms
        context_keywords = ["apply", "application", "workforce", "ccs", "child care", "childcare", "board"]
        has_context = any(kw in answer_lower for kw in context_keywords)
        assert has_context, (
            f"Follow-up response doesn't seem to reference CCS context: "
            f"'{data2['answer'][:150]}...'"
        )


class TestOpenAIAgentErrorHandling:
    """Tests for OpenAI Agent error handling."""

    def test_invalid_mode_returns_422(self, backend_server):
        """Invalid mode value should return 422."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": RELIABLE_QUESTION,
                "mode": "invalid_mode"
            }
        )
        assert r.status_code == 422

    def test_empty_question_returns_422(self, backend_server):
        """Empty question with openai_agent mode should return 422."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "",
                "mode": "openai_agent"
            }
        )
        assert r.status_code == 422
