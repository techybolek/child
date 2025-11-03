"""RAG handler for information queries using the existing retrieval pipeline"""

from .base import BaseHandler
from ..retriever import QdrantRetriever
from ..reranker import LLMJudgeReranker
from ..generator import ResponseGenerator
from .. import config


class RAGHandler(BaseHandler):
    """Handles information queries using RAG pipeline: Retrieval → Reranking → Generation"""

    def __init__(self, llm_model=None, reranker_model=None, provider=None, collection_name=None):
        """
        Initialize RAG handler with optional custom models and provider

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            provider: Optional provider ('groq' or 'openai') for all components
            collection_name: Optional Qdrant collection name
        """
        self.retriever = QdrantRetriever(collection_name=collection_name)

        # Use provider override or config default
        effective_provider = provider or config.LLM_PROVIDER

        # Initialize reranker with provider override or config default
        reranker_api_key = config.GROQ_API_KEY if effective_provider == 'groq' else config.OPENAI_API_KEY
        reranker_model_default = config.RERANKER_MODEL if not provider else (
            'openai/gpt-oss-20b' if provider == 'groq' else 'gpt-4o-mini'
        )
        self.reranker = LLMJudgeReranker(
            api_key=reranker_api_key,
            provider=effective_provider,
            model=reranker_model or reranker_model_default
        )

        # Initialize generator with provider override or config default
        generator_api_key = config.GROQ_API_KEY if effective_provider == 'groq' else config.OPENAI_API_KEY
        llm_model_default = config.LLM_MODEL if not provider else (
            'openai/gpt-oss-20b' if provider == 'groq' else 'gpt-4o-mini'
        )
        self.generator = ResponseGenerator(
            api_key=generator_api_key,
            provider=effective_provider,
            model=llm_model or llm_model_default
        )

    def handle(self, query: str) -> dict:
        """Run full RAG pipeline"""

        # Step 1: Retrieve
        chunks = self.retriever.search(query, top_k=config.RETRIEVAL_TOP_K)

        if not chunks:
            return {
                'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
                'sources': [],
                'response_type': 'information',
                'action_items': []
            }

        # Step 2: Rerank
        if self.reranker:
            chunks = self.reranker.rerank(query, chunks, top_k=config.RERANK_TOP_K)
        else:
            chunks = chunks[:config.RERANK_TOP_K]

        # Step 3: Generate
        result = self.generator.generate(query, chunks)

        # Step 4: Format response
        return {
            'answer': result['answer'],
            'sources': [
                {'doc': c['filename'], 'page': c['page'], 'url': c['source_url']}
                for c in chunks
            ],
            'response_type': 'information',
            'action_items': []
        }
