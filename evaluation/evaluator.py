import time
from chatbot.handlers.rag_handler import RAGHandler


class ChatbotEvaluator:
    def __init__(self, collection_name=None, retrieval_top_k=None):
        self.handler = RAGHandler(collection_name=collection_name, retrieval_top_k=retrieval_top_k)

    def query(self, question: str, debug: bool = False) -> dict:
        """Query chatbot and return response with timing"""
        start_time = time.time()
        response = self.handler.handle(question, debug=debug)
        response_time = time.time() - start_time

        result = {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response_time
        }

        # Include debug info if present
        if debug and 'debug_info' in response:
            result['debug_info'] = response['debug_info']

        return result
