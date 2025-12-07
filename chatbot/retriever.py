import time
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse, ResponseHandlingException
from langchain_openai import OpenAIEmbeddings
from . import config


def _retry_with_backoff(func, max_retries=None, base_delay=None):
    """
    Retry Qdrant operations with exponential backoff for transient errors.
    Handles HTTP errors (502/503/504) and timeouts.
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


class QdrantRetriever:
    def __init__(self, collection_name=None):
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL
        )
        self.collection = collection_name or config.COLLECTION_NAME
        print(f"[Retriever] Using Qdrant collection: {self.collection}")

    def search(self, query: str, top_k: int = 20):
        """Search Qdrant for relevant chunks (dense vectors only)"""
        print(f"[Retriever] Using Qdrant collection: {self.collection}")

        # Embed query
        query_vector = self.embeddings.embed_query(query)

        # Search (with retry for transient errors)
        # Use query_points with 'using' parameter for named vectors
        def _do_search():
            print("[Retriever] Performing Qdrant Dense search...")
            return self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                using="dense",  # Named vector for hybrid schema
                limit=top_k,
                score_threshold=config.MIN_SCORE_THRESHOLD
            ).points

        results = _retry_with_backoff(_do_search)

        # Return as simple dicts
        chunks = [
            {
                'text': hit.payload['text'],
                'score': hit.score,
                'filename': hit.payload.get('filename', ''),  # New loader uses 'filename'
                'page': hit.payload.get('page', 'N/A'),
                'source_url': hit.payload.get('source_url') or '',
                # Include context metadata for generation-time injection
                'master_context': hit.payload.get('master_context'),
                'document_context': hit.payload.get('document_context'),
                'chunk_context': hit.payload.get('chunk_context'),
            }
            for hit in results
        ]

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

        return chunks
