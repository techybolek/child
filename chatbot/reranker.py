from openai import OpenAI
from groq import Groq
import json
from . import config
from .prompts import RERANKING_PROMPT
from .reranker_adaptive import AdaptiveReranker


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

    def rerank(self, query: str, chunks: list, top_k: int = 7, adaptive: bool = None, debug: bool = False):
        """
        Rerank using LLM relevance scoring

        Args:
            query: User query
            chunks: List of retrieved chunks
            top_k: Maximum number of chunks to return (used when adaptive=False)
            adaptive: Whether to use adaptive selection (defaults to config.RERANK_ADAPTIVE_MODE)
            debug: Whether to include debug information

        Returns:
            Reranked chunks (and debug_info if debug=True)
        """
        debug_info = {}

        # Use config default if adaptive not specified
        if adaptive is None:
            adaptive = getattr(config, 'RERANK_ADAPTIVE_MODE', False)

        # Build prompt with full context information
        chunks_text_parts = []
        for i, chunk in enumerate(chunks):
            part = f"CHUNK {i}:\n"

            # Include chunk context if available (generated during indexing)
            if chunk.get('chunk_context'):
                part += f"[Context] {chunk['chunk_context']}\n"

            # Include the actual chunk text
            part += f"{chunk['text'][:600]}..."

            chunks_text_parts.append(part)

        chunks_text = "\n\n".join(chunks_text_parts)

        prompt = RERANKING_PROMPT.format(query=query, chunks_text=chunks_text)

        # Capture prompt for debug
        if debug:
            debug_info['reranker_prompt'] = prompt

        # Use the model passed in constructor (required)
        model = self.model

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

            # Capture reasoning for debug (available for reasoning models like gpt-oss)
            if debug:
                # Try to extract reasoning from the response
                reasoning = None

                # Check message level first (OpenAI/GROQ structure)
                if hasattr(response.choices[0].message, 'reasoning'):
                    reasoning = response.choices[0].message.reasoning

                # If not found, check top level (alternative structure)
                if not reasoning and hasattr(response, 'reasoning'):
                    reasoning = response.reasoning

                # Store reasoning or fallback message
                debug_info['reranker_reasoning'] = reasoning if reasoning else "No reasoning available (non-reasoning model)"

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

            # Store raw scores for debug
            if debug:
                debug_info['raw_scores'] = scores

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

        # Apply adaptive selection or traditional top-k
        if adaptive:
            print(f"[Reranker] Using adaptive selection (enabled)")

            # Initialize adaptive reranker with config
            adaptive_config = {
                'min_score': getattr(config, 'RERANK_MIN_SCORE', 0.60),
                'min_top_k': getattr(config, 'RERANK_MIN_TOP_K', 5),
                'max_top_k': getattr(config, 'RERANK_MAX_TOP_K', 12),
                'preferred_top_k': getattr(config, 'RERANK_PREFERRED_TOP_K', 7),
                'enumeration_patterns': getattr(config, 'ENUMERATION_PATTERNS', []),
                'single_fact_patterns': getattr(config, 'SINGLE_FACT_PATTERNS', [])
            }

            adaptive_reranker = AdaptiveReranker(adaptive_config)
            result_chunks = adaptive_reranker.adaptive_select(chunks, query)

            if debug:
                debug_info['adaptive_selection'] = {
                    'chunks_selected': len(result_chunks),
                    'score_range': f"{result_chunks[0]['final_score']:.2f} - {result_chunks[-1]['final_score']:.2f}" if result_chunks else "N/A"
                }
        else:
            print(f"[Reranker] Using traditional top-k selection (k={top_k})")

            # Sort and return top_k (use sorted() to avoid mutating original list)
            sorted_chunks = sorted(chunks, key=lambda c: c['final_score'], reverse=True)
            result_chunks = sorted_chunks[:top_k]

            if debug:
                debug_info['traditional_selection'] = {
                    'chunks_selected': len(result_chunks),
                    'top_k': top_k
                }

        if debug:
            return result_chunks, debug_info
        return result_chunks
