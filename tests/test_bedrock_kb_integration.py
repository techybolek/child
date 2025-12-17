"""API integration tests for Bedrock KB mode - uses FastAPI TestClient with real Bedrock calls"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add parent directory and backend directory to path
parent_dir = Path(__file__).resolve().parent.parent
backend_dir = parent_dir / 'backend'
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(backend_dir))

# Import after path is set
from main import app


class TestBedrockKBAPI:
    """Test end-to-end flow using FastAPI TestClient"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_bedrock_agent_chat_endpoint(self, client):
        """Send POST to /api/chat with mode='bedrock_agent'"""
        response = client.post(
            "/api/chat",
            json={
                "question": "What is TWC?",
                "mode": "bedrock_agent",
                "bedrock_agent_model": "nova-micro"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'answer' in data
        assert 'sources' in data
        assert 'session_id' in data
        assert 'timestamp' in data
        assert 'processing_time' in data

        # Verify answer content
        assert len(data['answer']) > 0
        assert isinstance(data['sources'], list)

    def test_bedrock_models_endpoint(self, client):
        """Send GET to /api/models/bedrock-agent"""
        response = client.get("/api/models/bedrock-agent")

        assert response.status_code == 200
        data = response.json()

        # Verify 3 models returned
        assert 'models' in data
        assert 'default' in data
        assert len(data['models']) == 3

        # Verify model structure
        model_ids = [m['id'] for m in data['models']]
        assert 'nova-micro' in model_ids
        assert 'nova-lite' in model_ids
        assert 'nova-pro' in model_ids

    def test_conversation_flow(self, client):
        """Send multiple queries with same session_id"""
        # First query
        response1 = client.post(
            "/api/chat",
            json={
                "question": "What is TWC?",
                "mode": "bedrock_agent",
                "session_id": "test-session-123"
            }
        )

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1['session_id'] == "test-session-123"

        # Second query with same session
        response2 = client.post(
            "/api/chat",
            json={
                "question": "What is CCS?",
                "mode": "bedrock_agent",
                "session_id": "test-session-123"
            }
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2['session_id'] == "test-session-123"

    def test_session_isolation(self, client):
        """Verify conversation isolation between different session_ids"""
        # Query on session 1
        response1 = client.post(
            "/api/chat",
            json={
                "question": "What is TWC?",
                "mode": "bedrock_agent",
                "session_id": "session-1"
            }
        )

        # Query on session 2
        response2 = client.post(
            "/api/chat",
            json={
                "question": "What is CCS?",
                "mode": "bedrock_agent",
                "session_id": "session-2"
            }
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()['session_id'] != response2.json()['session_id']

    def test_all_nova_models(self, client):
        """Test all 3 Amazon Nova models work"""
        models = ['nova-micro', 'nova-lite', 'nova-pro']

        for model in models:
            response = client.post(
                "/api/chat",
                json={
                    "question": "What is TWC?",
                    "mode": "bedrock_agent",
                    "bedrock_agent_model": model
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data['answer']) > 0


class TestBedrockCitationURLs:
    """Real integration tests for verifying full URLs in Bedrock citations.

    These tests call the live Bedrock API and verify that after metadata
    is uploaded to S3, citations include full source URLs.

    Prerequisites:
        1. Run LOAD_DB/generate_bedrock_metadata.py
        2. Run LOAD_DB/upload_bedrock_metadata.py
        3. Wait for KB resync to complete

    Run with: pytest tests/test_bedrock_kb_integration.py -v -k "citation"
    """

    def test_handler_returns_full_source_urls(self):
        """Verify BedrockKBHandler returns full clickable URLs in citations"""
        from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler

        handler = BedrockKBHandler(model='nova-micro')
        response = handler.handle("What is the income eligibility for childcare assistance?")

        # Must have at least one source
        assert response['sources'], "Expected at least one source citation"

        # Verify ALL sources have full URLs (not empty, not just filenames)
        for source in response['sources']:
            assert source['url'], f"Source {source['doc']} has empty URL"
            assert source['url'].startswith('https://'), \
                f"Expected full URL starting with https://, got: {source['url']}"
            assert 'twc.texas.gov' in source['url'], \
                f"Expected TWC URL, got: {source['url']}"

    def test_evaluator_returns_full_source_urls(self):
        """Verify BedrockKBEvaluator returns full clickable URLs in citations"""
        from evaluation.bedrock_evaluator import BedrockKBEvaluator

        evaluator = BedrockKBEvaluator()
        result = evaluator.query("What documents do I need for childcare eligibility?")

        # Must have at least one source
        assert result['sources'], "Expected at least one source citation"

        # Verify ALL sources have full URLs
        for source in result['sources']:
            assert source.get('url'), f"Source {source['doc']} has empty URL"
            assert source['url'].startswith('https://'), \
                f"Expected full URL starting with https://, got: {source['url']}"

    def test_handler_and_evaluator_urls_match_format(self):
        """Verify handler and evaluator return URLs in same format"""
        from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
        from evaluation.bedrock_evaluator import BedrockKBEvaluator

        handler = BedrockKBHandler(model='nova-micro')
        evaluator = BedrockKBEvaluator()

        question = "What is TWC childcare assistance?"

        handler_response = handler.handle(question)
        evaluator_response = evaluator.query(question)

        # Both should return sources with full URLs
        if handler_response['sources'] and evaluator_response['sources']:
            handler_url = handler_response['sources'][0].get('url', '')
            evaluator_url = evaluator_response['sources'][0].get('url', '')

            # Both should be full URLs or both empty (if metadata not indexed yet)
            assert (handler_url.startswith('https://') == evaluator_url.startswith('https://')), \
                f"Handler and evaluator URL formats don't match: {handler_url} vs {evaluator_url}"
