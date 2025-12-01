"""
Singleton wrapper for TexasChildcareChatbot

This service provides a singleton instance of the chatbot to avoid
reinitializing the expensive RAG pipeline on every request.
"""
import time
from typing import Dict, Any, Optional


def _get_chatbot_class():
    """Lazy import of chatbot to avoid sys.path pollution at module level."""
    import sys
    from pathlib import Path
    parent_dir = Path(__file__).resolve().parent.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from chatbot.chatbot import TexasChildcareChatbot
    return TexasChildcareChatbot


class ChatbotService:
    """
    Singleton wrapper for TexasChildcareChatbot

    Ensures only one instance of the chatbot is created and shared
    across all API requests, avoiding expensive reinitialization.
    """

    _instance: Optional['ChatbotService'] = None
    _chatbot = None  # Will be TexasChildcareChatbot instance

    def __new__(cls):
        """Ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'ChatbotService':
        """
        Get or create the singleton chatbot instance

        Returns:
            ChatbotService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
            TexasChildcareChatbot = _get_chatbot_class()
            cls._chatbot = TexasChildcareChatbot()
            print("✓ Chatbot instance created and initialized")
        return cls._instance

    def ask(self, question: str) -> Dict[str, Any]:
        """
        Ask the chatbot a question

        Args:
            question: User's question string

        Returns:
            Dictionary with:
                - answer: Generated answer text
                - sources: List of source citations
                - processing_time: Time taken to generate response

        Raises:
            Exception: If chatbot is not initialized or query fails
        """
        if self._chatbot is None:
            raise RuntimeError("Chatbot not initialized. Call get_instance() first.")

        # Track processing time
        start_time = time.time()

        try:
            # Call chatbot's ask method
            result = self._chatbot.ask(question)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Add processing time to result
            return {
                **result,
                'processing_time': round(processing_time, 2)
            }

        except Exception as e:
            processing_time = time.time() - start_time
            print(f"Error in chatbot query (took {processing_time:.2f}s): {str(e)}")
            raise

    def is_initialized(self) -> bool:
        """
        Check if chatbot is initialized

        Returns:
            bool: True if chatbot is ready to use
        """
        return self._chatbot is not None
