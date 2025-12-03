"""Base handler interface for intent-based routing"""


class BaseHandler:
    """Base class for all intent handlers"""

    def handle(self, query: str, thread_id: str | None = None) -> dict:
        """
        Process a user query and return response

        Args:
            query: User's question
            thread_id: Optional thread ID for conversation continuity

        Returns:
            dict with:
                - answer: str
                - sources: list
                - response_type: str
                - action_items: list (optional)
                - thread_id: str (if conversational)
                - turn_count: int (if conversational)
        """
        raise NotImplementedError("Subclasses must implement handle()")
