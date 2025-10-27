from openai import OpenAI
from groq import Groq
from .prompts import RESPONSE_GENERATION_PROMPT


class ResponseGenerator:
    def __init__(self, api_key: str, provider: str = 'groq', model: str = None):
        """
        Initialize the response generator

        Args:
            api_key: API key for the provider
            provider: 'groq' or 'openai'
            model: Model name to use (optional, will use default if not provided)
        """
        self.provider = provider
        self.model = model

        if provider == 'groq':
            self.client = Groq(api_key=api_key)
        else:
            self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, context_chunks: list):
        """Generate response with citations"""

        # Format context with citations
        context = self._format_context(context_chunks)

        # Build prompt
        prompt = RESPONSE_GENERATION_PROMPT.format(context=context, query=query)

        # Use the configured model or the one passed in constructor
        model = self.model or ("openai/gpt-oss-20b" if self.provider == 'groq' else "gpt-4-turbo-preview")

        print(f"[Generator] Using model: {model}")

        # Build API parameters
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }

        # GPT-5 only supports default temperature (1), don't set it
        if not model.startswith('gpt-5'):
            params['temperature'] = 0.1

        # Reasoning models (GPT-5, openai/gpt-oss) use reasoning tokens which count against limit
        # Need higher limit to leave room for actual response after reasoning
        if model.startswith('gpt-5') or model.startswith('openai/gpt-oss'):
            params['max_completion_tokens'] = 5000
        else:
            params['max_tokens'] = 1000

        # Generate
        try:
            response = self.client.chat.completions.create(**params)

            # Log full response for debugging
            print(f"[Generator] API Response: {response}")

            # Extract content with null check
            content = response.choices[0].message.content
            if content is None or content.strip() == '':
                print(f"[Generator] ERROR: Response content is empty")
                print(f"[Generator] Finish reason: {response.choices[0].finish_reason}")
                return {
                    'answer': 'I apologize, but I was unable to generate a response. Please try again.',
                    'usage': response.usage
                }

            print(f"[Generator] Response length: {len(content)} chars")
            return {
                'answer': content,
                'usage': response.usage
            }

        except Exception as e:
            print(f"[Generator] ERROR: {type(e).__name__}: {str(e)}")
            return {
                'answer': f'I apologize, but an error occurred while generating the response: {str(e)}',
                'usage': None
            }

    def _format_context(self, chunks: list):
        """Format chunks with citation markers"""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"[Doc {i}: {chunk['filename']}, Page {chunk['page']}]\n"
                f"{chunk['text']}\n"
            )
        return "\n".join(parts)
