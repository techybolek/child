from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from . import config


class QdrantRetriever:
    def __init__(self):
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL
        )
        self.collection = config.COLLECTION_NAME

    def search(self, query: str, top_k: int = 20):
        """Search Qdrant for relevant chunks"""
        # Embed query
        query_vector = self.embeddings.embed_query(query)

        # Search
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=config.MIN_SCORE_THRESHOLD
        )

        # Return as simple dicts
        return [
            {
                'text': hit.payload['text'],
                'score': hit.score,
                'filename': hit.payload.get('filename', ''),
                'page': hit.payload.get('page', 'N/A'),
                'source_url': hit.payload.get('source_url', ''),
                # Include context metadata for generation-time injection
                'master_context': hit.payload.get('master_context'),
                'document_context': hit.payload.get('document_context'),
                'chunk_context': hit.payload.get('chunk_context'),
            }
            for hit in results
        ]
