from .intent_router import IntentRouter


class TexasChildcareChatbot:
    def __init__(self):
        # Initialize intent router (handles all classification and routing)
        self.router = IntentRouter()

    def ask(self, question: str):
        """Ask a question, get an answer via intent-based routing"""
        return self.router.route(question)
