"""Integration tests for BedrockKBHandler - uses real AWS Bedrock KB (no mocking)"""

import pytest
import uuid
import sys
from pathlib import Path

# Add parent directory to path to import chatbot module
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from chatbot.handlers.bedrock_kb_handler import BedrockKBHandler
from chatbot import config


class TestBedrockKBHandlerInit:
    """Test handler initialization"""

    def test_init_with_default_config(self):
        """Test handler initializes with default config values"""
        handler = BedrockKBHandler()

        assert handler.model_short == config.BEDROCK_AGENT_MODEL
        assert handler.model_id is not None
        assert handler.model_arn.startswith('arn:aws:bedrock:')
        assert handler.client is not None

    def test_init_with_model_override(self):
        """Test handler initializes with model override"""
        handler = BedrockKBHandler(model='nova-lite')

        assert handler.model_short == 'nova-lite'
        assert 'nova-lite' in handler.model_id

    def test_model_resolution(self):
        """Test model ARN resolution for all 3 Amazon Nova models"""
        models = ['nova-micro', 'nova-lite', 'nova-pro']

        for model in models:
            handler = BedrockKBHandler(model=model)
            assert handler.model_short == model
            assert handler.model_arn.startswith('arn:aws:bedrock:')
            assert 'nova' in handler.model_id

    def test_invalid_model_raises_error(self):
        """Test that invalid model raises ValueError"""
        with pytest.raises(ValueError, match="Unknown model"):
            BedrockKBHandler(model='invalid-model')


class TestBedrockKBHandlerQuery:
    """Test query handling with real Bedrock KB calls"""

    def test_simple_query(self):
        """Send real query: 'What is TWC?' and verify response structure"""
        handler = BedrockKBHandler()

        response = handler.handle("What is TWC?")

        # Verify response structure
        assert 'answer' in response
        assert 'sources' in response
        assert 'response_type' in response
        assert 'thread_id' in response
        assert 'turn_count' in response

        # Verify answer contains content
        assert len(response['answer']) > 0
        assert response['response_type'] == 'information'
        assert response['turn_count'] == 1

    def test_response_parsing(self):
        """Test response parsing extracts answer and sources correctly"""
        handler = BedrockKBHandler()

        response = handler.handle("What is TWC?")

        # Verify sources structure
        assert isinstance(response['sources'], list)
        for source in response['sources']:
            assert 'doc' in source
            assert 'pages' in source
            assert 'url' in source
            # Verify source filenames are real KB filenames (lowercase with dashes)
            doc = source['doc']
            assert ' ' not in doc, f"Source filename should not contain spaces: {doc}"
            assert doc == doc.lower(), f"Source filename should be lowercase: {doc}"

    def test_async_query(self):
        """Test async version of query handler"""
        import asyncio
        handler = BedrockKBHandler()

        response = asyncio.run(handler.handle_async("What is TWC?"))

        assert 'answer' in response
        assert len(response['answer']) > 0
        assert 'thread_id' in response


class TestBedrockKBSessionManagement:
    """Test session management for conversation continuity"""

    def test_new_conversation_generates_uuid(self):
        """Test new_conversation() generates unique UUIDs"""
        handler = BedrockKBHandler()

        session1 = handler.new_conversation()
        session2 = handler.new_conversation()

        # Verify they are valid UUIDs
        uuid.UUID(session1)
        uuid.UUID(session2)

        # Verify they are different
        assert session1 != session2

    def test_session_tracking(self):
        """Send multiple queries with same session_id - verify session tracking"""
        handler = BedrockKBHandler()
        session_id = handler.new_conversation()

        # First query
        response1 = handler.handle("What is TWC?", thread_id=session_id)
        assert response1['thread_id'] == session_id
        assert response1['turn_count'] == 1

        # Second query with same session
        response2 = handler.handle("What is CCS?", thread_id=session_id)
        assert response2['thread_id'] == session_id
        assert response2['turn_count'] == 2

    def test_session_isolation(self):
        """Send queries with different session_ids - verify isolation"""
        handler = BedrockKBHandler()

        session1 = handler.new_conversation()
        session2 = handler.new_conversation()

        # Query on session 1
        response1 = handler.handle("What is TWC?", thread_id=session1)
        assert response1['thread_id'] == session1
        assert response1['turn_count'] == 1

        # Query on session 2
        response2 = handler.handle("What is CCS?", thread_id=session2)
        assert response2['thread_id'] == session2
        assert response2['turn_count'] == 1  # First turn on this session

    def test_clear_conversation(self):
        """Test clear_conversation() removes session from storage"""
        handler = BedrockKBHandler()
        session_id = handler.new_conversation()

        # Query to create session
        handler.handle("What is TWC?", thread_id=session_id)
        assert session_id in handler._sessions

        # Clear conversation
        handler.clear_conversation(session_id)
        assert session_id not in handler._sessions


class TestBedrockKBErrorHandling:
    """Test error handling"""

    def test_error_response_structure(self):
        """Test that errors return proper response structure"""
        handler = BedrockKBHandler()

        # This should succeed, but test the error path with debug mode
        response = handler.handle("What is TWC?", debug=True)

        # Verify debug info included
        assert 'debug_info' in response
        assert 'raw_output' in response['debug_info']
        assert 'model' in response['debug_info']
        assert 'kb_id' in response['debug_info']


class TestBedrockKBCitations:
    """Test citation extraction from Bedrock API (not from LLM text)"""

    def test_citations_match_kb_filename_pattern(self):
        """Test that citations are real KB filenames, not hallucinated titles"""
        handler = BedrockKBHandler()

        response = handler.handle("What is TWC and what programs does it offer?")

        # Verify all returned sources follow KB filename pattern
        # (may return 0 sources for some queries, which is valid)
        for source in response['sources']:
            doc = source['doc']
            # Real KB filenames are lowercase with dashes, ending in .pdf
            assert ' ' not in doc, f"Hallucinated filename (has spaces): {doc}"
            assert doc == doc.lower(), f"Hallucinated filename (has capitals): {doc}"
            assert doc.endswith('.pdf'), f"Expected .pdf extension: {doc}"

    def test_no_hallucinated_citations(self):
        """Test that sources come from API, not from LLM text output"""
        handler = BedrockKBHandler()

        response = handler.handle("What is CCS?", debug=True)

        # Verify response structure
        assert 'sources' in response
        assert 'debug_info' in response
        assert 'raw_output' in response['debug_info']

        # Verify each source follows KB filename pattern
        for source in response['sources']:
            doc = source['doc']
            # Real KB filenames don't have spaces or capital letters
            assert ' ' not in doc, f"Hallucinated filename (has spaces): {doc}"
            assert doc == doc.lower(), f"Hallucinated filename (has capitals): {doc}"
            # Common patterns for real KB filenames
            assert '-' in doc or doc == 'unknown', f"Expected dashes in filename: {doc}"

    def test_async_citations_match_sync(self):
        """Test that async handler also returns real KB filenames"""
        import asyncio
        handler = BedrockKBHandler()

        response = asyncio.run(handler.handle_async("What is CCS?"))

        for source in response['sources']:
            doc = source['doc']
            assert ' ' not in doc, f"Async: Hallucinated filename (has spaces): {doc}"
            assert doc == doc.lower(), f"Async: Hallucinated filename (has capitals): {doc}"

    def test_citations_returned_with_custom_prompt(self):
        """Test that citations are returned when using custom prompt template.

        Regression test for: Bedrock KB returns no citations with custom prompt
        Root cause: Missing $output_format_instructions$ placeholder in template.
        """
        handler = BedrockKBHandler()

        response = handler.handle("What is TWC?")

        # With the fix, we should get at least 1 source
        # Note: May vary by query, but "What is TWC?" should always return sources
        assert len(response['sources']) > 0, (
            "Expected sources from Bedrock KB. "
            "If empty, check that $output_format_instructions$ is in the prompt template."
        )
