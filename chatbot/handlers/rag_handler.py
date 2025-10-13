"""RAG handler for information queries using the existing retrieval pipeline"""

from .base import BaseHandler
from ..retriever import QdrantRetriever
from ..reranker import LLMJudgeReranker
from ..generator import ResponseGenerator
from .. import config


class RAGHandler(BaseHandler):
    """Handles information queries using RAG pipeline: Retrieval → Reranking → Generation"""

    def __init__(self):
        self.retriever = QdrantRetriever()

        # Initialize reranker
        reranker_api_key = config.GROQ_API_KEY if config.RERANKER_PROVIDER == 'groq' else config.OPENAI_API_KEY
        self.reranker = LLMJudgeReranker(
            api_key=reranker_api_key,
            provider=config.RERANKER_PROVIDER,
            model=config.RERANKER_MODEL
        )

        # Initialize generator
        generator_api_key = config.GROQ_API_KEY if config.LLM_PROVIDER == 'groq' else config.OPENAI_API_KEY
        self.generator = ResponseGenerator(
            api_key=generator_api_key,
            provider=config.LLM_PROVIDER,
            model=config.LLM_MODEL
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
