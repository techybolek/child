import pytest
import requests

RELIABLE_QUESTION = "What is CCS?"


class TestHealthEndpoint:
    def test_returns_200_with_status(self, backend_server):
        r = requests.get(f"{backend_server}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "chatbot_initialized" in data
        assert data["chatbot_initialized"] is True


class TestModelsEndpoint:
    def test_returns_200_with_structure(self, backend_server):
        r = requests.get(f"{backend_server}/api/models")
        assert r.status_code == 200
        data = r.json()
        assert "provider" in data
        assert "generators" in data


class TestChatEndpoint:
    def test_valid_request_returns_200(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert "timestamp" in data
        assert "processing_time" in data
        assert data["processing_time"] > 0

    def test_session_id_generated_when_missing(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert r.status_code == 200
        assert r.json()["session_id"] is not None

    def test_session_id_preserved_when_provided(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "session_id": "test-123"}
        )
        assert r.status_code == 200
        assert r.json()["session_id"] == "test-123"


class TestRequestValidation:
    def test_empty_question_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": ""}
        )
        assert r.status_code == 422

    def test_question_too_long_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": "x" * 501}
        )
        assert r.status_code == 422

    def test_missing_question_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={}
        )
        assert r.status_code == 422


class TestConversationalMode:
    def test_conversational_mode_returns_200(self, backend_server):
        """Conversational mode with session_id should work without errors."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": RELIABLE_QUESTION,
                "session_id": "conv-test-123",
                "conversational_mode": True
            }
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "answer" in data
        assert data["session_id"] == "conv-test-123"

    def test_conversational_mode_preserves_history(self, backend_server):
        """Follow-up question with same session_id should use conversation context.

        Bug reproduced: Both requests show "[Reformulate Node] No history" in logs,
        meaning the second request loses context and "what about 5" retrieves 0 chunks
        instead of being reformulated to "what assistance can a family of 5 expect".
        """
        import uuid
        session_id = f"conv-history-test-{uuid.uuid4()}"

        # Turn 1: Ask about family of 4
        r1 = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "what assistance can a family of 4 expect",
                "session_id": session_id,
                "conversational_mode": True
            }
        )
        assert r1.status_code == 200
        data1 = r1.json()
        assert "answer" in data1
        # First response should have actual content (not fallback)
        assert len(data1["answer"]) > 50, "First response should have substantial content"

        # Turn 2: Follow-up that requires context from Turn 1
        r2 = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "what about 5",
                "session_id": session_id,
                "conversational_mode": True
            }
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert "answer" in data2

        # The bug: without history, "what about 5" retrieves 0 chunks and returns fallback
        # With proper history, it should reformulate to "what assistance can a family of 5 expect"
        # and return a substantive answer about family of 5
        assert len(data2["answer"]) > 50, (
            "Follow-up response is too short - likely no context was preserved. "
            "Expected reformulation of 'what about 5' to include family context."
        )
        # Additional check: response should not be the "I don't have information" fallback
        fallback_indicators = ["don't have", "cannot find", "no information", "unable to"]
        answer_lower = data2["answer"].lower()
        is_fallback = any(indicator in answer_lower for indicator in fallback_indicators)
        assert not is_fallback, (
            f"Response appears to be a fallback: '{data2['answer'][:100]}...' "
            "This indicates conversation history was not preserved."
        )

        # Check the response relates to the original context (family/income/assistance)
        # If history was lost, the answer to "what about 5" will be nonsensical
        context_keywords = ["family", "income", "eligibility", "assistance", "smi", "limit"]
        answer_has_context = any(kw in answer_lower for kw in context_keywords)
        assert answer_has_context, (
            f"Response to 'what about 5' doesn't reference family/income context: "
            f"'{data2['answer'][:150]}...' - conversation history may not be preserved."
        )


class TestResponseHeaders:
    def test_process_time_header_present(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert "x-process-time" in r.headers
