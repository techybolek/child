import time
from .graph.builder import get_graph


class TexasChildcareChatbot:
    def __init__(self, llm_model=None, reranker_model=None, intent_model=None, provider=None):
        """
        Initialize chatbot with LangGraph-based RAG pipeline

        Args:
            llm_model: Optional model for generation (currently unused, for API compatibility)
            reranker_model: Optional model for reranking (currently unused, for API compatibility)
            intent_model: Optional model for intent classification (currently unused, for API compatibility)
            provider: Optional provider (currently unused, for API compatibility)
        """
        self.graph = get_graph()
        print("✓ Chatbot instance created (LangGraph)")

    def ask(self, question: str, debug: bool = False):
        """
        Ask a question, route through LangGraph pipeline

        Args:
            question: User's question
            debug: Enable debug output with retrieval/reranking details

        Returns:
            dict with answer, sources, response_type, action_items, processing_time
        """
        start_time = time.time()

        initial_state = {
            "query": question,
            "debug": debug,
            "intent": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "answer": None,
            "sources": [],
            "response_type": "",
            "action_items": [],
            "debug_info": {} if debug else None
        }

        final_state = self.graph.invoke(initial_state)

        result = {
            'answer': final_state['answer'],
            'sources': final_state['sources'],
            'response_type': final_state['response_type'],
            'action_items': final_state['action_items']
        }

        if debug:
            result['debug_info'] = final_state.get('debug_info', {})

        result['processing_time'] = round(time.time() - start_time, 2)

        return result
