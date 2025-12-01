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


class TestResponseHeaders:
    def test_process_time_header_present(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert "x-process-time" in r.headers
