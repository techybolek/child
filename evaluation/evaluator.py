import time
from chatbot.chatbot import TexasChildcareChatbot


class ChatbotEvaluator:
    def __init__(self):
        self.chatbot = TexasChildcareChatbot()

    def query(self, question: str) -> dict:
        """Query chatbot and return response with timing"""
        start_time = time.time()
        response = self.chatbot.ask(question)
        response_time = time.time() - start_time

        return {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response_time
        }
