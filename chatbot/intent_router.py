"""Intent classification and routing for query handling"""

from openai import OpenAI
from groq import Groq
from . import config
from .handlers import RAGHandler, LocationSearchHandler


class IntentRouter:
    """Classifies user queries and routes to appropriate handlers"""

    def __init__(self):
        # Initialize LLM client for intent classification
        if config.INTENT_CLASSIFIER_PROVIDER == 'groq':
            self.client = Groq(api_key=config.GROQ_API_KEY)
        else:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        # Initialize handlers
        self.handlers = {
            'location_search': LocationSearchHandler(),
            'information': RAGHandler()
        }

        print(f"Intent Router initialized with {config.INTENT_CLASSIFIER_PROVIDER.upper()} - {config.INTENT_CLASSIFIER_MODEL}")

    def classify_intent(self, query: str) -> str:
        """
        Classify query intent using LLM

        Args:
            query: User's question

        Returns:
            Intent string: 'location_search' or 'information'
        """
        prompt = f"""Classify this user query into ONE category:

Categories:
- location_search: User wants to FIND or SEARCH for childcare facilities/providers near a location (e.g., "find daycare near me", "search for providers in Austin", "where can I find childcare")
- information: User wants INFORMATION about policies, eligibility, programs, requirements, income limits, application process, etc.

Rules:
- If query mentions "find", "search", "near", "location", or "where can I" → location_search
- If query asks "what", "how", "who qualifies", "income limits", "requirements" → information
- Default to information if uncertain

Query: "{query}"

Respond with ONLY the category name (location_search or information):"""

        response = self.client.chat.completions.create(
            model=config.INTENT_CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10
        )

        intent = response.choices[0].message.content.strip().lower()

        # Validate intent
        if intent not in self.handlers:
            intent = 'information'  # Default fallback

        return intent

    def route(self, query: str) -> dict:
        """
        Classify intent and route to appropriate handler

        Args:
            query: User's question

        Returns:
            Handler response dict
        """
        # Classify intent
        intent = self.classify_intent(query)
        print(f"Intent classified: {intent}")

        # Get handler and process
        handler = self.handlers[intent]
        return handler.handle(query)
