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
        # Use specific phrases to avoid false positives (e.g., "families don't have to pay")
        fallback_indicators = ["i don't have information", "i cannot find", "no information available", "i'm unable to"]
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


class TestRetrievalMode:
    def test_dense_mode_returns_200(self, backend_server):
        """Dense retrieval mode should work."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "retrieval_mode": "dense"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 10

    def test_hybrid_mode_returns_200(self, backend_server):
        """Hybrid retrieval mode should work."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "retrieval_mode": "hybrid"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 10

    def test_kendra_mode_returns_200_or_config_error(self, backend_server):
        """Kendra retrieval mode should work if configured, or return clear error."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "retrieval_mode": "kendra"}
        )
        # Kendra may not be configured (no AWS creds) - that's OK, just verify we get a response
        if r.status_code == 200:
            data = r.json()
            assert "answer" in data
            assert len(data["answer"]) > 10
        else:
            # If Kendra fails, it should be due to configuration, not a code bug
            assert r.status_code == 500
            # The error should mention AWS/Kendra/credentials
            data = r.json()
            error_str = str(data).lower()
            assert any(term in error_str for term in ["kendra", "aws", "credential", "botocore", "failed"]), \
                f"Expected Kendra-related error, got: {data}"

    def test_invalid_retrieval_mode_returns_400(self, backend_server):
        """Invalid retrieval mode should return 400."""
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "retrieval_mode": "invalid"}
        )
        assert r.status_code == 400
        data = r.json()
        assert "dense" in str(data).lower() or "hybrid" in str(data).lower()


class TestSourceValidation:
    def test_kendra_source_page_is_valid_integer(self, backend_server):
        """Sources must have integer page values, not 'N/A' strings.

        Bug: Kendra retriever returns page='N/A' which fails Source model validation.
        This causes a 500 error instead of a successful response.
        """
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "what assistance can a family of 4 expect",
                "retrieval_mode": "kendra",
                "conversational_mode": True
            }
        )
        # Should not fail with 500 due to page validation
        if r.status_code == 200:
            data = r.json()
            for source in data.get("sources", []):
                assert isinstance(source["page"], int), \
                    f"Source page must be int, got {type(source['page'])}: {source['page']}"
        # If Kendra not configured, that's fine - but should NOT be a validation error
        elif r.status_code == 500:
            data = r.json()
            detail = data.get("detail", {})
            error_type = detail.get("error_type", "") if isinstance(detail, dict) else str(detail)
            error_msg = str(detail)
            # The bug: ValidationError indicates page='N/A' failed Source model validation
            assert "ValidationError" not in error_type and "int_parsing" not in error_msg, \
                f"Source validation failed - page is likely not an integer: {error_msg}"

    def test_source_url_is_valid_string(self, backend_server):
        """Source URL must be a string (empty or valid URL), never None.

        Bug: Qdrant returning source_url=None caused string concatenation error.
        Fix: Retrievers use `or ''` pattern to convert None to empty string.
        """
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": "What is CCS?"}
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()

        for source in data.get("sources", []):
            assert isinstance(source.get("url"), str), \
                f"Source URL must be string, got {type(source.get('url'))}: {source}"
            # URL should be either empty string or valid URL starting with http
            url = source.get("url", "")
            assert url == "" or url.startswith("http"), \
                f"Source URL should be empty or valid URL, got: {url}"


class TestResponseHeaders:
    def test_process_time_header_present(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert "x-process-time" in r.headers


def parse_sse_events(response_text: str) -> list:
    """Parse SSE events from response text."""
    import json
    events = []
    current_event = {}
    for line in response_text.split('\n'):
        if line.startswith('event: '):
            current_event['type'] = line[7:].strip()
        elif line.startswith('data: '):
            current_event['data'] = json.loads(line[6:])
            events.append(current_event)
            current_event = {}
    return events


class TestChatStreamEndpoint:
    def test_stream_returns_200_with_sse_content_type(self, backend_server):
        """Streaming endpoint should return SSE content type."""
        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={"question": RELIABLE_QUESTION},
            stream=True
        )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("Content-Type", "")

    def test_stream_yields_token_events(self, backend_server):
        """Streaming should yield token events with content."""
        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={"question": RELIABLE_QUESTION},
            stream=True
        )
        assert r.status_code == 200

        events = parse_sse_events(r.text)
        token_events = [e for e in events if e.get('type') == 'token']

        assert len(token_events) > 0, "Expected at least one token event"
        for event in token_events:
            assert 'content' in event['data'], "Token event should have content field"

    def test_stream_yields_done_event_with_metadata(self, backend_server):
        """Streaming should end with done event containing metadata."""
        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={"question": RELIABLE_QUESTION},
            stream=True
        )
        assert r.status_code == 200

        events = parse_sse_events(r.text)
        done_events = [e for e in events if e.get('type') == 'done']

        assert len(done_events) == 1, "Expected exactly one done event"
        done_data = done_events[0]['data']

        assert 'answer' in done_data
        assert 'sources' in done_data
        assert 'response_type' in done_data
        assert 'session_id' in done_data
        assert 'processing_time' in done_data
        assert done_data['processing_time'] > 0

    def test_stream_session_id_preserved(self, backend_server):
        """Session ID should be preserved in done event."""
        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={"question": RELIABLE_QUESTION, "session_id": "stream-test-123"},
            stream=True
        )
        assert r.status_code == 200

        events = parse_sse_events(r.text)
        done_events = [e for e in events if e.get('type') == 'done']

        assert len(done_events) == 1
        assert done_events[0]['data']['session_id'] == "stream-test-123"

    def test_stream_conversational_mode_works(self, backend_server):
        """Streaming with conversational mode should work."""
        import uuid
        session_id = f"stream-conv-test-{uuid.uuid4()}"

        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={
                "question": RELIABLE_QUESTION,
                "session_id": session_id,
                "conversational_mode": True
            },
            stream=True
        )
        assert r.status_code == 200

        events = parse_sse_events(r.text)
        done_events = [e for e in events if e.get('type') == 'done']

        assert len(done_events) == 1, "Expected done event"
        assert done_events[0]['data']['session_id'] == session_id

    def test_stream_location_search_returns_done_immediately(self, backend_server):
        """Location search should return done event without token streaming."""
        r = requests.post(
            f"{backend_server}/api/chat/stream",
            json={"question": "where is the nearest daycare in Austin"},
            stream=True
        )
        assert r.status_code == 200

        events = parse_sse_events(r.text)
        token_events = [e for e in events if e.get('type') == 'token']
        done_events = [e for e in events if e.get('type') == 'done']

        # Location search should skip token streaming
        assert len(token_events) == 0, "Location search should not yield token events"
        assert len(done_events) == 1, "Expected done event"
        assert done_events[0]['data']['response_type'] == "location_search"
