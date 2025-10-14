"""Intent classification and routing for query handling"""

from openai import OpenAI
from groq import Groq
from . import config
from .handlers import RAGHandler, LocationSearchHandler
from .prompts import INTENT_CLASSIFICATION_PROMPT


class IntentRouter:
    """Classifies user queries and routes to appropriate handlers"""

    def __init__(self, llm_model=None, reranker_model=None, intent_model=None, provider=None):
        """
        Initialize intent router with optional custom models and provider

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            intent_model: Optional model for intent classification
            provider: Optional provider ('groq' or 'openai') for all components
        """
        # Use provider override or config default
        effective_provider = provider or config.INTENT_CLASSIFIER_PROVIDER

        # Initialize LLM client for intent classification
        if effective_provider == 'groq':
            self.client = Groq(api_key=config.GROQ_API_KEY)
        else:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        # Store model override or use config default
        intent_model_default = config.INTENT_CLASSIFIER_MODEL if not provider else (
            'llama-3.3-70b-versatile' if provider == 'groq' else 'gpt-4o-mini'
        )
        self.intent_model = intent_model or intent_model_default

        # Initialize handlers with model params
        self.handlers = {
            'location_search': LocationSearchHandler(),
            'information': RAGHandler(llm_model=llm_model, reranker_model=reranker_model, provider=provider)
        }

        print(f"Intent Router initialized with {effective_provider.upper()} - {self.intent_model}")

    def classify_intent(self, query: str) -> str:
        """
        Classify query intent using LLM

        Args:
            query: User's question

        Returns:
            Intent string: 'location_search' or 'information'
        """
        print(f"[Intent Classifier] Using model: {self.intent_model}")
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
        print(f"[Intent Classifier] Prompt:\n{prompt}\n")

        # Build API parameters
        params = {
            "model": self.intent_model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # GPT-5 only supports default temperature (1), don't set it
        if not self.intent_model.startswith('gpt-5'):
            params['temperature'] = 0

        # GPT-5 models use max_completion_tokens, older models use max_tokens
        # GPT-5 uses reasoning tokens which count against the limit, so need higher limit
        if self.intent_model.startswith('gpt-5'):
            params['max_completion_tokens'] = 200
        else:
            params['max_tokens'] = 50

        try:
            response = self.client.chat.completions.create(**params)

            # Log full response for debugging
            print(f"[Intent Classifier] API Response: {response}")

            # Extract content with null check
            content = response.choices[0].message.content
            if content is None:
                print(f"[Intent Classifier] WARNING: Response content is None, defaulting to 'information'")
                return 'information'

            intent = content.strip().lower()
            print(f"[Intent Classifier] Raw response: {intent}")

            # Validate intent
            if intent not in self.handlers:
                print(f"[Intent Classifier] WARNING: Unknown intent '{intent}', defaulting to 'information'")
                intent = 'information'  # Default fallback

            print(f"[Intent Classifier] Classified as: {intent}")
            return intent

        except Exception as e:
            print(f"[Intent Classifier] ERROR: {type(e).__name__}: {str(e)}")
            print(f"[Intent Classifier] Defaulting to 'information' due to error")
            return 'information'

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
