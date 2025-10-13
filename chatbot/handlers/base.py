"""Base handler interface for intent-based routing"""


class BaseHandler:
    """Base class for all intent handlers"""

    def handle(self, query: str) -> dict:
        """
        Process a user query and return response

        Args:
            query: User's question

        Returns:
            dict with:
                - answer: str
                - sources: list
                - response_type: str
                - action_items: list (optional)
        """
        raise NotImplementedError("Subclasses must implement handle()")
