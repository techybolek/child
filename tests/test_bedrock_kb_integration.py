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
