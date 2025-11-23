import sys
import os
import time
from typing import List, Dict

# Add LOAD_DB to path for BM25Embedder import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LOAD_DB'))

from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector as QdrantSparseVector
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from langchain_openai import OpenAIEmbeddings
from LOAD_DB.sparse_embedder import BM25Embedder
from . import config


def _retry_with_backoff(func, max_retries=None, base_delay=None):
    """
    Retry Qdrant operations with exponential backoff for transient errors.
    Handles HTTP errors (502/503/504) and timeouts.

    Args:
        func: Callable to execute
        max_retries: Number of retry attempts (default: config.QDRANT_MAX_RETRIES)
        base_delay: Base delay in seconds (default: config.QDRANT_RETRY_BASE_DELAY)

    Returns:
        Result of func() if successful

    Raises:
        Exception: If all retries exhausted or non-retryable error
    """
    max_retries = max_retries or config.QDRANT_MAX_RETRIES
    base_delay = base_delay or config.QDRANT_RETRY_BASE_DELAY

    for attempt in range(max_retries):
        try:
            return func()
        except (UnexpectedResponse, ResponseHandlingException) as e:
            is_retryable = False
            error_msg = str(e)

            if isinstance(e, UnexpectedResponse) and e.status_code in (502, 503, 504):
                is_retryable = True
                error_msg = f"HTTP {e.status_code}"
            elif isinstance(e, ResponseHandlingException):
                is_retryable = True
                error_msg = "timeout"

            if is_retryable and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[Retry] Qdrant {error_msg}, attempt {attempt + 1}/{max_retries}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise


class QdrantHybridRetriever:
    """
    Hybrid retriever combining dense (OpenAI) and sparse (BM25) vectors with RRF fusion.

    Compatible with QdrantRetriever interface - can be used as a drop-in replacement.

    Architecture:
    - Dense vectors: OpenAI embeddings (1536-dim) for semantic similarity
    - Sparse vectors: BM25 term frequencies for keyword matching
    - Fusion: Reciprocal Rank Fusion (RRF) via Qdrant Query API

    Usage:
        retriever = QdrantHybridRetriever(collection_name='tro-child-hybrid-v1')
        results = retriever.search(query="What is BCY-26?", top_k=20)
    """

    def __init__(self, collection_name=None):
        """
        Initialize hybrid retriever with both dense and sparse embedders.

        Args:
            collection_name: Qdrant collection to search (default: config.COLLECTION_NAME)
        """
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL
        )
        self.sparse_embedder = BM25Embedder(vocab_size=config.BM25_VOCABULARY_SIZE)
        self.collection = collection_name or config.COLLECTION_NAME
        print(f"[HybridRetriever] Using Qdrant collection: {self.collection}")
        print(f"[HybridRetriever] Fusion method: RRF (k={config.RRF_K})")

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        """
        Search using hybrid retrieval with RRF fusion.

        Process:
        1. Generate dense query vector (OpenAI)
        2. Generate sparse query vector (BM25)
        3. Prefetch top-100 from each vector type
        4. Fuse results using RRF (Reciprocal Rank Fusion)
        5. Return top-K fused results

        Args:
            query: Query string
            top_k: Number of results to return

        Returns:
            List of dicts with keys: text, score, filename, page, source_url,
            master_context, document_context, chunk_context
        """
        print(f"[HybridRetriever] Using Qdrant collection: {self.collection}")
        print(f"[HybridRetriever] Searching with RRF fusion (top_k={top_k})")

        # Generate dense query vector
        dense_query = self.embeddings.embed_query(query)

        # Generate sparse query vector and convert to Qdrant format
        sparse_result = self.sparse_embedder.embed_query(query)
        sparse_query = QdrantSparseVector(
            indices=sparse_result.indices,
            values=sparse_result.values
        )

        # Qdrant Query API with RRF fusion (with retry for transient errors)
        try:
            def _do_query():
                return self.client.query_points(
                    collection_name=self.collection,
                    prefetch=[
                        # Prefetch dense candidates
                        Prefetch(
                            query=dense_query,
                            using="dense",
                            limit=config.HYBRID_PREFETCH_LIMIT
                        ),
                        # Prefetch sparse candidates
                        Prefetch(
                            query=sparse_query,
                            using="sparse",
                            limit=config.HYBRID_PREFETCH_LIMIT
                        )
                    ],
                    query=FusionQuery(
                        fusion=Fusion.RRF
                    ),
                    limit=top_k,
                    score_threshold=0.05  # RRF scores are lower than cosine similarity
                )

            results = _retry_with_backoff(_do_query)
        except Exception as e:
            print(f"[HybridRetriever] ERROR in query_points: {e}")
            print(f"[HybridRetriever] Falling back to dense-only search")
            return self._dense_only_fallback(query, top_k)

        # Format results to match QdrantRetriever interface
        chunks = self._format_results(results.points)

        # CRITICAL: Detect duplicate chunks (should never happen)
        seen_texts = set()
        for i, chunk in enumerate(chunks):
            text = chunk['text']
            if text in seen_texts:
                raise ValueError(
                    f"DUPLICATE CHUNK DETECTED at index {i}!\n"
                    f"Text preview: {text[:200]}...\n"
                    f"This indicates a data loading bug. Check vector database for duplicates."
                )
            seen_texts.add(text)

        print(f"[HybridRetriever] Returned {len(chunks)} chunks after RRF fusion")
        return chunks

    def _format_results(self, points) -> List[Dict]:
        """
        Format Qdrant results to match QdrantRetriever interface.

        Args:
            points: ScoredPoint objects from Qdrant query_points

        Returns:
            List of dicts with standard retriever keys
        """
        return [
            {
                'text': point.payload['text'],
                'score': point.score,
                'filename': point.payload.get('filename', ''),
                'page': point.payload.get('page', 'N/A'),
                'source_url': point.payload.get('source_url', ''),
                # Include context metadata for generation-time injection
                'master_context': point.payload.get('master_context'),
                'document_context': point.payload.get('document_context'),
                'chunk_context': point.payload.get('chunk_context'),
            }
            for point in points
        ]

    def _dense_only_fallback(self, query: str, top_k: int) -> List[Dict]:
        """
        Fallback to dense-only search if hybrid fails.

        This ensures backward compatibility if hybrid collection is unavailable
        or if there's an error in the RRF fusion process.

        Args:
            query: Query string
            top_k: Number of results to return

        Returns:
            List of dicts from dense-only search
        """
        print(f"[HybridRetriever] Running dense-only fallback")

        # Embed query
        query_vector = self.embeddings.embed_query(query)

        # Search dense vectors only (with retry for transient errors)
        def _do_search():
            return self.client.search(
                collection_name=self.collection,
                query_vector=("dense", query_vector),  # Named vector syntax
                limit=top_k,
                score_threshold=config.MIN_SCORE_THRESHOLD
            )

        results = _retry_with_backoff(_do_search)

        # Format results
        chunks = [
            {
                'text': hit.payload['text'],
                'score': hit.score,
                'filename': hit.payload.get('filename', ''),
                'page': hit.payload.get('page', 'N/A'),
                'source_url': hit.payload.get('source_url', ''),
                'master_context': hit.payload.get('master_context'),
                'document_context': hit.payload.get('document_context'),
                'chunk_context': hit.payload.get('chunk_context'),
            }
            for hit in results
        ]

        print(f"[HybridRetriever] Fallback returned {len(chunks)} chunks")
        return chunks
