from .intent_router import IntentRouter


class TexasChildcareChatbot:
    def __init__(self, llm_model=None, reranker_model=None, intent_model=None, provider=None):
        """
        Initialize chatbot with optional custom models and provider

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            intent_model: Optional model for intent classification
            provider: Optional provider ('groq' or 'openai') for all components
        """
        # Initialize intent router (handles all classification and routing)
        self.router = IntentRouter(
            llm_model=llm_model,
            reranker_model=reranker_model,
            intent_model=intent_model,
            provider=provider
        )

    def ask(self, question: str):
        """Ask a question, get an answer via intent-based routing"""
        return self.router.route(question)
