from openai import OpenAI
from groq import Groq
import json
from . import config
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
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "seed": config.SEED,
        }

        # Reasoning models (GPT-5, openai/gpt-oss) use reasoning tokens which count against limit
        # Need higher limit to leave room for JSON output after reasoning
        if model.startswith('gpt-5') or model.startswith('openai/gpt-oss'):
            params['max_completion_tokens'] = 4000
        else:
            params['max_tokens'] = 2000

        # Get scores
        try:
            response = self.client.chat.completions.create(**params)

            # Log full response for debugging
            print(f"[Reranker] API Response: {response}")

            # Extract content with null check
            content = response.choices[0].message.content
            if content is None or content.strip() == '':
                print(f"[Reranker] ERROR: Response content is empty")
                print(f"[Reranker] Finish reason: {response.choices[0].finish_reason}")
                print(f"[Reranker] Using fallback: returning chunks in original order")
                # Return chunks with default scores
                for i, chunk in enumerate(chunks):
                    chunk['final_score'] = 0.5
                return chunks[:top_k]

            print(f"[Reranker] Raw response length: {len(content)} chars")
            scores = json.loads(content)

        except json.JSONDecodeError as e:
            print(f"[Reranker] JSON Parse Error: {str(e)}")
            print(f"[Reranker] Response content: {content[:200]}...")
            # Return chunks with default scores
            for i, chunk in enumerate(chunks):
                chunk['final_score'] = 0.5
            return chunks[:top_k]

        except Exception as e:
            print(f"[Reranker] ERROR: {type(e).__name__}: {str(e)}")
            # Return chunks with default scores
            for i, chunk in enumerate(chunks):
                chunk['final_score'] = 0.5
            return chunks[:top_k]

        # Update scores
        for i, chunk in enumerate(chunks):
            chunk['final_score'] = scores.get(f"chunk_{i}", 0) / 10.0

        # Sort and return top_k
        chunks.sort(key=lambda c: c['final_score'], reverse=True)
        return chunks[:top_k]
