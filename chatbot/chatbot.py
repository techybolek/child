from .intent_router import IntentRouter
import time


class TexasChildcareChatbot:
    def __init__(self, llm_model=None, reranker_model=None, intent_model=None, provider=None):
        """
        Initialize chatbot with intent routing and optional custom models

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            intent_model: Optional model for intent classification
            provider: Optional provider ('groq' or 'openai') for all components
        """
        # Initialize intent router with all handlers
        self.router = IntentRouter(
            llm_model=llm_model,
            reranker_model=reranker_model,
            intent_model=intent_model,
            provider=provider
        )
        print("✓ Chatbot instance created and initialized")

    def ask(self, question: str):
        """
        Ask a question, route through intent classifier to appropriate handler

        Args:
            question: User's question

        Returns:
            dict with answer, sources, response_type, action_items, processing_time
        """
        start_time = time.time()

        # Route query through intent classifier
        result = self.router.route(question)

        # Add processing time
        result['processing_time'] = round(time.time() - start_time, 2)

        return result
