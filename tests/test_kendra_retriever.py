"""Minimal tests for Kendra LangGraph integration.

Tests the KendraRetriever class and its integration with the LangGraph pipeline.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from chatbot import config


class TestKendraRetriever:
    """Unit tests for KendraRetriever class."""

    def test_kendra_retriever_initializes(self):
        """Verify KendraRetriever can be instantiated."""
        from chatbot.kendra_retriever import KendraRetriever
        retriever = KendraRetriever()
        assert retriever.retriever is not None
        assert retriever.index_id == config.KENDRA_INDEX_ID
        print("✓ KendraRetriever initialized successfully")

    def test_kendra_search_returns_correct_structure(self):
        """Verify search() returns chunks in expected format."""
        from chatbot.kendra_retriever import KendraRetriever
        retriever = KendraRetriever()
        results = retriever.search("What is CCS?", top_k=3)

        assert isinstance(results, list)
        print(f"  Retrieved {len(results)} chunks")

        if results:
            chunk = results[0]
            # Must have same keys as QdrantRetriever
            required_keys = {'text', 'score', 'filename', 'page', 'source_url',
                           'master_context', 'document_context', 'chunk_context'}
            actual_keys = set(chunk.keys())
            missing = required_keys - actual_keys
            assert not missing, f"Missing required keys: {missing}"
            print(f"✓ Chunk structure is correct: {list(chunk.keys())}")
        else:
            print("  Warning: No results returned (may be expected for some queries)")


class TestKendraInPipeline:
    """Integration tests for Kendra in LangGraph pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Override config to use Kendra."""
        self.original_mode = config.RETRIEVAL_MODE
        config.RETRIEVAL_MODE = 'kendra'
        yield
        config.RETRIEVAL_MODE = self.original_mode

    def test_chatbot_with_kendra_returns_valid_response(self):
        """Verify full chatbot pipeline works with Kendra."""
        from chatbot.chatbot import TexasChildcareChatbot
        chatbot = TexasChildcareChatbot()
        result = chatbot.ask("What is Parent Share of Cost?")

        assert 'answer' in result
        assert len(result['answer']) > 10, "Answer too short"
        assert 'sources' in result
        assert isinstance(result['sources'], list)
        print(f"✓ Chatbot returned valid response ({len(result['answer'])} chars)")

    def test_kendra_via_retrieval_mode_override(self):
        """Verify retrieval_mode parameter works."""
        # Reset to dense (override fixture)
        config.RETRIEVAL_MODE = 'dense'

        from chatbot.chatbot import TexasChildcareChatbot
        chatbot = TexasChildcareChatbot(retrieval_mode='kendra')
        result = chatbot.ask("What is CCS?")

        assert 'answer' in result
        assert len(result['answer']) > 10, "Answer too short"
        print(f"✓ retrieval_mode override works ({len(result['answer'])} chars)")


class TestRetrievalModeRouting:
    """Tests for retrieval mode routing in retrieve_node."""

    def test_retrieve_node_routes_to_dense(self):
        """Verify retrieve_node uses dense retriever when mode is dense."""
        from chatbot.graph.nodes.retrieve import retrieve_node

        state = {
            "query": "What is CCS?",
            "retrieval_mode_override": "dense",
            "debug": False
        }
        result = retrieve_node(state)

        assert 'retrieved_chunks' in result
        assert isinstance(result['retrieved_chunks'], list)
        print(f"✓ Dense mode returned {len(result['retrieved_chunks'])} chunks")

    def test_retrieve_node_routes_to_hybrid(self):
        """Verify retrieve_node uses hybrid retriever when mode is hybrid."""
        from chatbot.graph.nodes.retrieve import retrieve_node

        state = {
            "query": "What is CCS?",
            "retrieval_mode_override": "hybrid",
            "debug": False
        }
        result = retrieve_node(state)

        assert 'retrieved_chunks' in result
        assert isinstance(result['retrieved_chunks'], list)
        print(f"✓ Hybrid mode returned {len(result['retrieved_chunks'])} chunks")

    def test_retrieve_node_routes_to_kendra(self):
        """Verify retrieve_node uses Kendra retriever when mode is kendra."""
        from chatbot.graph.nodes.retrieve import retrieve_node

        state = {
            "query": "What is CCS?",
            "retrieval_mode_override": "kendra",
            "debug": False
        }
        result = retrieve_node(state)

        assert 'retrieved_chunks' in result
        assert isinstance(result['retrieved_chunks'], list)
        print(f"✓ Kendra mode returned {len(result['retrieved_chunks'])} chunks")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KENDRA RETRIEVER TESTS")
    print("=" * 60 + "\n")

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
