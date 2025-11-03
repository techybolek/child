import time
from chatbot.handlers.rag_handler import RAGHandler


class ChatbotEvaluator:
    def __init__(self, collection_name=None):
        self.handler = RAGHandler(collection_name=collection_name)

    def query(self, question: str) -> dict:
        """Query chatbot and return response with timing"""
        start_time = time.time()
        response = self.handler.handle(question)
        response_time = time.time() - start_time

        return {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response_time
        }
