"""
Contextual Processor for generating document and chunk contexts.

Uses GROQ API to generate three-tier context hierarchy:
1. Master Context (static, all documents)
2. Document Context (generated per PDF)
3. Chunk Context (generated per chunk)
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional

from groq import Groq

import config
from prompts import (
    MASTER_CONTEXT,
    build_chunk_context_prompt,
    build_document_context_prompt,
)

logger = logging.getLogger(__name__)


class ContextualChunkProcessor:
    """Generates contextual metadata for documents and chunks using GROQ API."""

    def __init__(self, groq_api_key: str, model: str):
        """
        Initialize the contextual processor.

        Args:
            groq_api_key: GROQ API key
            model: GROQ model name (e.g., 'openai/gpt-oss-20b')
        """
        self.client = Groq(api_key=groq_api_key)
        self.model = model
        self.master_context = MASTER_CONTEXT
        self.retry_count = 3
        self.retry_delay = 1  # seconds, increases exponentially

    def _make_api_call(
        self,
        prompt: str,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """
        Make a GROQ API call with exponential backoff retry logic.

        Args:
            prompt: The prompt to send to GROQ
            max_tokens: Maximum tokens in response

        Returns:
            Response content or None if failed after retries
        """
        for attempt in range(self.retry_count):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    seed=42,
                    max_completion_tokens=max_tokens,
                )

                content = response.choices[0].message.content
                if content is None or content.strip() == "":
                    logger.warning("API returned empty content, retrying...")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    return None

                return content.strip()

            except Exception as e:
                logger.error(
                    f"API error on attempt {attempt + 1}/{self.retry_count}: {type(e).__name__}: {str(e)}"
                )
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    return None

        return None

    def generate_document_context(
        self,
        pdf_id: str,
        document_title: str,
        total_pages: int,
        first_2000_chars: str,
    ) -> Optional[str]:
        """
        Generate document-level context (Tier 2).

        Args:
            pdf_id: Unique identifier for the PDF (usually filename without extension)
            document_title: Original filename
            total_pages: Total pages in document
            first_2000_chars: First 2000 characters of document content

        Returns:
            Generated context string or None if generation failed
        """
        cache_path = os.path.join(
            config.LOAD_DB_CHECKPOINTS_DIR, f"doc_context_{pdf_id}.json"
        )

        # Check cache first
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                    logger.info(f"Using cached document context for {pdf_id}")
                    return cached.get("document_context")
            except Exception as e:
                logger.warning(f"Failed to read cache for {pdf_id}: {e}")

        # Generate new context
        logger.info(f"Generating document context for {pdf_id}...")
        prompt = build_document_context_prompt(
            document_title,
            total_pages,
            first_2000_chars,
        )

        context = self._make_api_call(prompt, max_tokens=500)

        if context:
            # Save to cache
            try:
                os.makedirs(config.LOAD_DB_CHECKPOINTS_DIR, exist_ok=True)
                with open(cache_path, "w") as f:
                    json.dump({"document_context": context, "pdf_id": pdf_id}, f)
                logger.info(f"Cached document context for {pdf_id}")
            except Exception as e:
                logger.warning(f"Failed to cache document context: {e}")

            logger.info(f"Generated document context for {pdf_id}")
            return context
        else:
            logger.error(f"Failed to generate document context for {pdf_id}")
            return None

    def generate_chunk_contexts_batch(
        self,
        chunks: List[Dict],
        document_context: str,
    ) -> Optional[Dict[int, str]]:
        """
        Generate chunk-level contexts in a batch (Tier 3).

        Args:
            chunks: List of chunk dictionaries with:
                - page_num: Page number
                - total_pages: Total pages in document
                - chunk_index: Index of chunk
                - total_chunks: Total chunks in document
                - chunk_text: The chunk content
            document_context: Document-level context from Tier 2

        Returns:
            Dictionary mapping chunk_index to generated context, or None if failed
        """
        if not chunks:
            return {}

        logger.info(f"Generating contexts for batch of {len(chunks)} chunks...")

        contexts = {}
        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i + 1}/{len(chunks)} in batch...")

            prompt = build_chunk_context_prompt(
                document_context,
                chunk["chunk_text"],
            )

            context = self._make_api_call(prompt, max_tokens=300)

            if context:
                contexts[chunk["chunk_index"]] = context
            else:
                logger.warning(
                    f"Failed to generate context for chunk {chunk['chunk_index']}"
                )

        logger.info(
            f"Generated {len(contexts)}/{len(chunks)} chunk contexts in batch"
        )
        return contexts if contexts else None

    def generate_all_chunk_contexts(
        self,
        all_chunks: List[Dict],
        document_context: str,
    ) -> Optional[Dict[int, str]]:
        """
        Generate chunk-level contexts for all chunks with rate limiting.

        Args:
            all_chunks: List of all chunk dictionaries
            document_context: Document-level context

        Returns:
            Dictionary mapping chunk_index to context
        """
        all_contexts = {}

        for batch_start in range(0, len(all_chunks), config.CONTEXT_BATCH_SIZE):
            batch_end = min(
                batch_start + config.CONTEXT_BATCH_SIZE, len(all_chunks)
            )
            batch = all_chunks[batch_start:batch_end]

            batch_contexts = self.generate_chunk_contexts_batch(
                batch, document_context
            )

            if batch_contexts:
                all_contexts.update(batch_contexts)

            # Rate limiting between batches
            if batch_end < len(all_chunks):
                logger.debug(
                    f"Rate limiting: sleeping {config.CONTEXT_RATE_LIMIT_DELAY}s before next batch..."
                )
                time.sleep(config.CONTEXT_RATE_LIMIT_DELAY)

        logger.info(
            f"Generated {len(all_contexts)}/{len(all_chunks)} total chunk contexts"
        )
        return all_contexts if all_contexts else None
