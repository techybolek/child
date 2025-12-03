import re
from openai import OpenAI
from groq import Groq
from . import config
from .prompts import RESPONSE_GENERATION_PROMPT, CONVERSATIONAL_RESPONSE_PROMPT
from .prompts.abbreviations import ABBREVIATIONS


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

    def generate(self, query: str, context_chunks: list, recent_history: str = None):
        """Generate response with citations.

        Args:
            query: The user's question (reformulated if in conversational mode)
            context_chunks: List of reranked chunks with text, filename, page, etc.
            recent_history: Optional formatted conversation history for multi-hop reasoning
        """

        # Format context with citations
        context = self._format_context(context_chunks)

        # Build prompt - use conversational prompt if history is provided
        if recent_history:
            prompt = CONVERSATIONAL_RESPONSE_PROMPT.format(
                history=recent_history,
                context=context,
                query=query
            )
        else:
            prompt = RESPONSE_GENERATION_PROMPT.format(context=context, query=query)

        # Use the model passed in constructor (required)
        model = self.model

        print(f"[Generator] Using model: {model}")

        # Build API parameters
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "seed": config.SEED,
        }

        # Reasoning models (GPT-5, openai/gpt-oss) use reasoning tokens which count against limit
        # Need higher limit to leave room for actual response after reasoning
        if model.startswith('gpt-5') or model.startswith('openai/gpt-oss'):
            params['max_completion_tokens'] = 5000
        else:
            params['max_tokens'] = 1000

        # Generate
        try:
            response = self.client.chat.completions.create(**params)

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

    def generate_stream(self, query: str, context_chunks: list, recent_history: str = None):
        """Generate response with streaming - yields tokens as they arrive.

        Args:
            query: The user's question (reformulated if in conversational mode)
            context_chunks: List of reranked chunks with text, filename, page, etc.
            recent_history: Optional formatted conversation history for multi-hop reasoning

        Yields:
            str: Individual tokens as they are generated
        """
        # Format context with citations
        context = self._format_context(context_chunks)

        # Build prompt - use conversational prompt if history is provided
        if recent_history:
            prompt = CONVERSATIONAL_RESPONSE_PROMPT.format(
                history=recent_history,
                context=context,
                query=query
            )
        else:
            prompt = RESPONSE_GENERATION_PROMPT.format(context=context, query=query)

        model = self.model
        print(f"[Generator] Streaming with model: {model}")

        # Build API parameters
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "seed": config.SEED,
            "stream": True,
        }

        # Reasoning models use reasoning tokens which count against limit
        if model.startswith('gpt-5') or model.startswith('openai/gpt-oss'):
            params['max_completion_tokens'] = 5000
        else:
            params['max_tokens'] = 1000

        try:
            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"[Generator] STREAM ERROR: {type(e).__name__}: {str(e)}")
            yield f"\n\n[Error: {str(e)}]"

    def _format_context(self, chunks: list):
        """Format chunks with citation markers and injected contexts"""
        parts = []
        master_context_injected = False
        abbreviations_injected = False
        last_filename = None

        # Detect abbreviations once
        abbreviations_glossary = self._detect_abbreviations(chunks)

        for i, chunk in enumerate(chunks, 1):
            # Inject master context once at the beginning
            if not master_context_injected and chunk.get('master_context'):
                parts.append(f"[System Context]\n{chunk['master_context']}\n")
                master_context_injected = True

            # Inject abbreviations after master context
            if master_context_injected and not abbreviations_injected and abbreviations_glossary:
                parts.append(f"[Abbreviations]\n{abbreviations_glossary}\n")
                abbreviations_injected = True

            # Inject document context when switching to a new document
            if chunk['filename'] != last_filename and chunk.get('document_context'):
                parts.append(f"[Document Context: {chunk['filename']}]\n{chunk['document_context']}\n")
                last_filename = chunk['filename']

            # Build chunk entry with optional chunk context
            chunk_entry = f"[Doc {i}: {chunk['filename']}, Page {chunk['page']}]\n"
            if chunk.get('chunk_context'):
                chunk_entry += f"{chunk['chunk_context']}\n\n"
            chunk_entry += chunk['text']

            parts.append(chunk_entry)

        return "\n".join(parts)

    def _detect_abbreviations(self, chunks: list):
        """Detect abbreviations in chunks and return glossary"""
        detected = set()

        # Combine all text from chunks
        combined_text = " ".join([
            chunk.get('text', '') + " " +
            chunk.get('chunk_context', '') + " " +
            chunk.get('document_context', '')
            for chunk in chunks
        ])

        # Find abbreviations that appear in the text
        for abbr in ABBREVIATIONS.keys():
            # Match whole word abbreviations (word boundaries)
            if re.search(r'\b' + re.escape(abbr) + r'\b', combined_text):
                detected.add(abbr)

        # Build glossary if abbreviations detected
        if detected:
            glossary_lines = [f"- {abbr}: {ABBREVIATIONS[abbr]}" for abbr in sorted(detected)]
            return "\n".join(glossary_lines)

        return None
