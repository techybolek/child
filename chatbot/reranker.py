from openai import OpenAI
from groq import Groq
import json


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

        prompt = f"""Score how relevant each chunk is to this question (0-10):

Question: {query}

{chunks_text}

Return JSON: {{"chunk_0": <score>, "chunk_1": <score>, ...}}"""

        # Use the configured model or the one passed in constructor
        model = self.model or ("openai/gpt-oss-20b" if self.provider == 'groq' else "gpt-4o-mini")

        # Get scores
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        scores = json.loads(response.choices[0].message.content)

        # Update scores
        for i, chunk in enumerate(chunks):
            chunk['final_score'] = scores.get(f"chunk_{i}", 0) / 10.0

        # Sort and return top_k
        chunks.sort(key=lambda c: c['final_score'], reverse=True)
        return chunks[:top_k]
