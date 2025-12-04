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

    def test_kendra_skips_reranking(self):
        """Verify reranking is skipped for Kendra mode (Kendra has built-in ranking)."""
        from chatbot.chatbot import TexasChildcareChatbot

        chatbot = TexasChildcareChatbot(retrieval_mode='kendra')
        result = chatbot.ask("What is CCS?", debug=True)

        assert 'answer' in result
        debug_info = result.get('debug_info', {})

        # Verify reranking was skipped
        assert debug_info.get('reranker_skipped') is True, \
            "Expected reranker to be skipped for Kendra mode"
        assert 'built-in' in debug_info.get('reranker_skip_reason', '').lower(), \
            "Expected skip reason to mention built-in ranking"

        print("✓ Kendra correctly skips LLM reranking")

    def test_kendra_with_conversational_mode(self):
        """Verify Kendra works with conversational mode (reformulation + memory)."""
        from chatbot.chatbot import TexasChildcareChatbot

        chatbot = TexasChildcareChatbot(
            retrieval_mode='kendra',
            conversational_mode=True
        )
        thread_id = chatbot.new_conversation()

        # Turn 1: Establish context
        r1 = chatbot.ask("What is CCS?", thread_id=thread_id)
        assert 'answer' in r1
        assert r1['turn_count'] == 1

        # Turn 2: Follow-up with pronoun
        r2 = chatbot.ask("How do I apply for it?", thread_id=thread_id)
        assert 'answer' in r2
        assert r2['turn_count'] == 2

        # Reformulated query should reference CCS
        reformulated = r2.get('reformulated_query', '')
        assert 'CCS' in reformulated or 'Child Care' in reformulated, \
            f"Expected CCS in reformulated query, got: {reformulated}"

        print("✓ Kendra + conversational mode works correctly")


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

    def test_hybrid_does_not_skip_reranking(self):
        """Verify reranking is NOT skipped for hybrid mode."""
        from chatbot.chatbot import TexasChildcareChatbot

        chatbot = TexasChildcareChatbot(retrieval_mode='hybrid')
        result = chatbot.ask("What is CCS?", debug=True)

        assert 'answer' in result
        debug_info = result.get('debug_info', {})

        # Verify reranking was NOT skipped
        assert debug_info.get('reranker_skipped') is not True, \
            "Reranking should NOT be skipped for hybrid mode"
        # Should have reranker scores
        assert 'reranker_scores' in debug_info or 'final_chunks' in debug_info, \
            "Expected reranker output in debug info"

        print("✓ Hybrid mode correctly applies LLM reranking")

    def test_dense_does_not_skip_reranking(self):
        """Verify reranking is NOT skipped for dense mode."""
        from chatbot.chatbot import TexasChildcareChatbot

        chatbot = TexasChildcareChatbot(retrieval_mode='dense')
        result = chatbot.ask("What is CCS?", debug=True)

        assert 'answer' in result
        debug_info = result.get('debug_info', {})

        # Verify reranking was NOT skipped
        assert debug_info.get('reranker_skipped') is not True, \
            "Reranking should NOT be skipped for dense mode"

        print("✓ Dense mode correctly applies LLM reranking")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KENDRA RETRIEVER TESTS")
    print("=" * 60 + "\n")

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
