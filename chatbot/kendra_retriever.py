"""KendraRetriever - AWS Kendra retriever with same interface as QdrantRetriever."""

from langchain_aws import AmazonKendraRetriever
from . import config


class KendraRetriever:
    """AWS Kendra retriever with same interface as QdrantRetriever.

    Enables Kendra to be used as a drop-in replacement in the LangGraph pipeline.
    """

    def __init__(self, index_id=None, region=None, top_k=None):
        """Initialize Kendra retriever.

        Args:
            index_id: Kendra index ID (defaults to config.KENDRA_INDEX_ID)
            region: AWS region (defaults to config.KENDRA_REGION)
            top_k: Number of results to retrieve (defaults to config.KENDRA_TOP_K)
        """
        self.index_id = index_id or config.KENDRA_INDEX_ID
        self.region = region or config.KENDRA_REGION
        self.default_top_k = top_k or config.KENDRA_TOP_K

        self.retriever = AmazonKendraRetriever(
            index_id=self.index_id,
            region_name=self.region,
            top_k=self.default_top_k,
            min_score_confidence=0.0
        )
        print(f"[KendraRetriever] Using Kendra index: {self.index_id}")

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """Search Kendra for relevant chunks.

        Args:
            query: Search query string
            top_k: Number of results to return (defaults to config.KENDRA_TOP_K)

        Returns:
            List of chunk dictionaries with keys: text, score, filename, page,
            source_url, master_context, document_context, chunk_context
        """
        effective_top_k = top_k or self.default_top_k
        print(f"[KendraRetriever] Searching Kendra for: {query[:50]}...")

        # Retrieve from Kendra
        kendra_docs = self.retriever.invoke(query)

        # Convert to standard chunk format
        chunks = self._convert_to_chunks(kendra_docs[:effective_top_k])

        print(f"[KendraRetriever] Retrieved {len(chunks)} chunks")
        return chunks

    def _convert_to_chunks(self, docs) -> list[dict]:
        """Convert Kendra documents to chunk dict format matching QdrantRetriever.

        Args:
            docs: List of LangChain Document objects from Kendra

        Returns:
            List of chunk dictionaries compatible with reranker and generator
        """
        chunks = []
        for doc in docs:
            chunk = {
                # Required fields (same as QdrantRetriever)
                'text': doc.page_content,
                'score': doc.metadata.get('score', 0.0),
                'filename': doc.metadata.get('source') or doc.metadata.get('title', 'Unknown'),
                'page': int(doc.metadata.get('page', 0)) if str(doc.metadata.get('page', '')).isdigit() else 0,
                'source_url': doc.metadata.get('source_uri') or doc.metadata.get('document_uri', ''),

                # Context fields (empty for Kendra - it doesn't have these)
                'master_context': '',
                'document_context': '',
                'chunk_context': '',
            }
            chunks.append(chunk)
        return chunks
