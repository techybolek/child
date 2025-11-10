"""RAG handler for information queries using the existing retrieval pipeline"""

from .base import BaseHandler
from ..retriever import QdrantRetriever
from ..reranker import LLMJudgeReranker
from ..generator import ResponseGenerator
from .. import config


class RAGHandler(BaseHandler):
    """Handles information queries using RAG pipeline: Retrieval → Reranking → Generation"""

    def __init__(self, llm_model=None, reranker_model=None, provider=None, collection_name=None, retrieval_top_k=None):
        """
        Initialize RAG handler with optional custom models and provider

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            provider: Optional provider ('groq' or 'openai') for all components
            collection_name: Optional Qdrant collection name
            retrieval_top_k: Optional override for number of chunks to retrieve
        """
        self.retriever = QdrantRetriever(collection_name=collection_name)
        self.retrieval_top_k = retrieval_top_k

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

    def handle(self, query: str, debug: bool = False) -> dict:
        """Run full RAG pipeline"""
        debug_data = {}

        # Step 1: Retrieve
        top_k = self.retrieval_top_k or config.RETRIEVAL_TOP_K
        retrieved_chunks = self.retriever.search(query, top_k=top_k)

        if not retrieved_chunks:
            return {
                'answer': "I couldn't find information about that. Try calling 1-800-862-5252.",
                'sources': [],
                'response_type': 'information',
                'action_items': []
            }

        # Store retrieved chunks for debug
        if debug:
            debug_data['retrieved_chunks'] = [
                {
                    'doc': c.get('filename', ''),
                    'page': c.get('page', ''),
                    'score': c.get('score', 0),
                    'text': c.get('text', '')
                }
                for c in retrieved_chunks
            ]

        # Step 2: Rerank
        if self.reranker:
            if debug:
                reranked_chunks, reranker_debug = self.reranker.rerank(query, retrieved_chunks, top_k=config.RERANK_TOP_K, debug=True)
                debug_data['reranker_scores'] = reranker_debug.get('raw_scores', {})
            else:
                reranked_chunks = self.reranker.rerank(query, retrieved_chunks, top_k=config.RERANK_TOP_K)
        else:
            reranked_chunks = retrieved_chunks[:config.RERANK_TOP_K]

        # Store final chunks for debug
        if debug:
            debug_data['final_chunks'] = [
                {
                    'doc': c.get('filename', ''),
                    'page': c.get('page', ''),
                    'text': c.get('text', '')
                }
                for c in reranked_chunks
            ]

        # Step 3: Generate
        result = self.generator.generate(query, reranked_chunks)

        # Step 4: Format response
        # Extract only the sources that were actually cited in the answer
        cited_sources = self._extract_cited_sources(result['answer'], reranked_chunks)

        response = {
            'answer': result['answer'],
            'sources': cited_sources,
            'response_type': 'information',
            'action_items': []
        }

        # Include debug info if requested
        if debug:
            response['debug_info'] = debug_data

        return response

    def _extract_cited_sources(self, answer: str, chunks: list) -> list:
        """Extract only the sources that were actually cited in the answer"""
        import re

        # Find all [Doc N] citations in the answer
        cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+)\]', answer))

        # Map citation numbers to chunk metadata
        cited_sources = []
        for doc_num in sorted(cited_doc_nums, key=int):
            idx = int(doc_num) - 1  # Convert to 0-based index
            if 0 <= idx < len(chunks):
                cited_sources.append({
                    'doc': chunks[idx]['filename'],
                    'page': chunks[idx]['page'],
                    'url': chunks[idx]['source_url']
                })

        return cited_sources
