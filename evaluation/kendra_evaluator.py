"""Kendra evaluator using unified LangGraph pipeline"""

import time
from chatbot.chatbot import TexasChildcareChatbot


class KendraEvaluator:
    """Evaluator that uses Kendra retrieval through LangGraph pipeline"""

    def __init__(self):
        self.chatbot = TexasChildcareChatbot(
            retrieval_mode='kendra',
            conversational_mode=False
        )

    def query(self, question: str, debug: bool = False) -> dict:
        """Query Kendra-based chatbot and return response with timing"""
        start_time = time.time()
        response = self.chatbot.ask(question, debug=debug)
        response_time = time.time() - start_time

        result = {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response_time
        }

        if debug and 'debug_info' in response:
            result['debug_info'] = response['debug_info']

        return result
