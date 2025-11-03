"""
Contextual Chunk Processor - Three-tier context generation using GROQ
"""

import json
import logging
import os
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests

from prompts import MASTER_CONTEXT, build_document_context_prompt, build_chunk_context_prompt

logger = logging.getLogger(__name__)


class ContextualChunkProcessor:
    """Generates three-tier contextual metadata for chunks using GROQ API."""
    
    def __init__(self, groq_api_key: str, model: str = 'openai/gpt-oss-20b'):
        """
        Initialize the contextual processor.
        
        Args:
            groq_api_key: GROQ API key
            model: Model to use (default: openai/gpt-oss-20b)
        """
        self.api_key = groq_api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.master_context = MASTER_CONTEXT
        
        # Checkpoints directory for caching document contexts
        self.checkpoints_dir = Path(__file__).parent / 'checkpoints'
        self.checkpoints_dir.mkdir(exist_ok=True)
        
    def _make_groq_request(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        """
        Call GROQ API with exponential backoff retry logic.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                
                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {delay}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(delay)
                    continue
                
                elif response.status_code >= 500:
                    # Server error - retry
                    logger.warning(f"Server error {response.status_code}. Retrying...")
                    time.sleep(base_delay * (attempt + 1))
                    continue
                
                else:
                    logger.error(f"GROQ API error {response.status_code}: {response.text}")
                    return None
            
            except requests.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (attempt + 1))
                continue
            
            except Exception as e:
                logger.error(f"Error calling GROQ API: {e}")
                return None
        
        logger.error(f"Failed to generate context after {max_retries} retries")
        return None
    
    def generate_document_context(
        self,
        pdf_id: str,
        document_title: str,
        total_pages: int,
        first_2000_chars: str,
        source_url: str = ""
    ) -> Optional[str]:
        """
        Generate Tier 2 document-level context.
        
        Args:
            pdf_id: PDF identifier (without extension)
            document_title: Filename
            total_pages: Total pages
            first_2000_chars: First 2000 characters of content
            source_url: Source URL (optional)
        
        Returns:
            Generated document context or None if failed
        """
        # Check cache first
        cache_file = self.checkpoints_dir / f"doc_context_{pdf_id}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    logger.info(f"Loaded cached document context for {pdf_id}")
                    return cached['context']
            except Exception as e:
                logger.warning(f"Failed to load cache for {pdf_id}: {e}")
        
        # Generate new context
        logger.info(f"Generating document context for {pdf_id}")
        
        prompt = build_document_context_prompt(
            master_context=self.master_context,
            document_title=document_title,
            source_url=source_url,
            total_pages=total_pages,
            first_2000_chars=first_2000_chars
        )
        
        context = self._make_groq_request(prompt, max_tokens=2000)
        
        if context:
            # Cache it
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'pdf_id': pdf_id,
                        'context': context,
                        'timestamp': time.time()
                    }, f)
                logger.info(f"Cached document context for {pdf_id}")
            except Exception as e:
                logger.warning(f"Failed to cache document context: {e}")
        
        return context
    
    def generate_chunk_contexts_batch(
        self,
        chunks: List[Dict[str, Any]],
        document_context: str
    ) -> List[Dict[str, Any]]:
        """
        Generate Tier 3 chunk-level contexts for a batch of chunks.
        
        Args:
            chunks: List of chunk dicts with keys: chunk_text, page_num, chunk_index, total_chunks, total_pages
            document_context: Tier 2 document context
        
        Returns:
            List of chunk dicts with added 'chunk_context' key
        """
        logger.info(f"Generating chunk contexts for batch of {len(chunks)} chunks")
        
        for chunk in chunks:
            prompt = build_chunk_context_prompt(
                document_context=document_context,
                chunk_text=chunk['chunk_text']
            )
            
            chunk_context = self._make_groq_request(prompt, max_tokens=2000)
            chunk['chunk_context'] = chunk_context if chunk_context else ""
            
            logger.debug(f"Generated context for chunk {chunk['chunk_index']}/{chunk['total_chunks']}: {chunk_context[:80]}...")
        
        return chunks

    def generate_all_chunk_contexts(
        self,
        chunks: List[Dict[str, Any]],
        document_context: str
    ) -> Dict[int, str]:
        """
        Generate Tier 3 chunk-level contexts for all chunks in batches.
        
        Args:
            chunks: List of chunk dicts with keys: text, page_num, chunk_index, total_chunks, total_pages
            document_context: Tier 2 document context
        
        Returns:
            Dict mapping chunk index to generated chunk context
        """
        logger.info(f"Generating chunk contexts for {len(chunks)} total chunks")
        
        chunk_contexts = {}
        batch_size = 10
        
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch = chunks[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)")
            
            # Generate contexts for this batch
            batch_with_contexts = self.generate_chunk_contexts_batch(batch, document_context)
            
            # Extract contexts from batch
            for i, chunk in enumerate(batch_with_contexts):
                original_index = batch_start + i
                chunk_contexts[original_index] = chunk.get('chunk_context', '')
            
            # Rate limit between batches
            if batch_end < len(chunks):
                import config
                delay = config.CONTEXT_RATE_LIMIT_DELAY
                logger.info(f"Rate limiting: waiting {delay}s before next batch")
                time.sleep(delay)
        
        logger.info(f"Generated contexts for {len(chunk_contexts)} chunks")
        return chunk_contexts
