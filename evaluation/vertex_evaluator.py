"""Vertex AI Agent evaluator wrapper for evaluation framework"""

import time
from chatbot.handlers.vertex_agent_handler import VertexAgentHandler


class VertexAgentEvaluator:
    """Evaluator that uses VertexAgentHandler for retrieval and generation"""

    def __init__(self):
        self.handler = VertexAgentHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        """Query Vertex AI Agent handler and return response with timing"""
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
