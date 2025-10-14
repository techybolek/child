from openai import OpenAI
from groq import Groq
import json
from .prompts import RERANKING_PROMPT


class LLMJudgeReranker:
    def __init__(self, api_key: str, provider: str = 'groq', model: str = None):
        """
        Initialize the reranker

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

    def rerank(self, query: str, chunks: list, top_k: int = 7):
        """Rerank using LLM relevance scoring"""

        # Build prompt
        chunks_text = "\n\n".join([
            f"CHUNK {i}:\n{chunk['text'][:300]}..."
            for i, chunk in enumerate(chunks)
        ])

        prompt = RERANKING_PROMPT.format(query=query, chunks_text=chunks_text)

        # Use the configured model or the one passed in constructor
        model = self.model or ("openai/gpt-oss-20b" if self.provider == 'groq' else "gpt-4o-mini")

        print(f"[Reranker] Using model: {model}")

        # Build API parameters
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        # GPT-5 only supports default temperature (1), don't set it
        if not model.startswith('gpt-5'):
            params['temperature'] = 0.1

        # GPT-5 models use max_completion_tokens, older models use max_tokens
        if model.startswith('gpt-5'):
            params['max_completion_tokens'] = 2000
        else:
            params['max_tokens'] = 2000

        # Get scores
        response = self.client.chat.completions.create(**params)

        scores = json.loads(response.choices[0].message.content)

        # Update scores
        for i, chunk in enumerate(chunks):
            chunk['final_score'] = scores.get(f"chunk_{i}", 0) / 10.0

        # Sort and return top_k
        chunks.sort(key=lambda c: c['final_score'], reverse=True)
        return chunks[:top_k]
