"""RAG handler for information queries using the existing retrieval pipeline"""

from .base import BaseHandler
from ..retriever import QdrantRetriever
from ..hybrid_retriever import QdrantHybridRetriever
from ..reranker import LLMJudgeReranker
from ..generator import ResponseGenerator
from ..utils import extract_cited_sources
from .. import config


class RAGHandler(BaseHandler):
    """Handles information queries using RAG pipeline: Retrieval → Reranking → Generation"""

    def __init__(self, llm_model=None, reranker_model=None, provider=None, collection_name=None, retrieval_top_k=None, retrieval_mode=None):
        """
        Initialize RAG handler with optional custom models and provider

        Args:
            llm_model: Optional model for generation
            reranker_model: Optional model for reranking
            provider: Optional provider ('groq' or 'openai') for all components
            collection_name: Optional Qdrant collection name
            retrieval_top_k: Optional override for number of chunks to retrieve
            retrieval_mode: Optional retrieval mode ('hybrid' or 'dense'), defaults to config.RETRIEVAL_MODE
        """
        # Choose retriever based on mode (parameter overrides config)
        mode = retrieval_mode or config.RETRIEVAL_MODE
        if mode == 'hybrid':
            self.retriever = QdrantHybridRetriever(collection_name=collection_name)
        else:
            self.retriever = QdrantRetriever(collection_name=collection_name)
        self.retrieval_top_k = retrieval_top_k

        # Use provider override or config default
        effective_provider = provider or config.LLM_PROVIDER

        # Initialize reranker with config defaults
        reranker_api_key = config.GROQ_API_KEY if effective_provider == 'groq' else config.OPENAI_API_KEY
        self.reranker = LLMJudgeReranker(
            api_key=reranker_api_key,
            provider=effective_provider,
            model=reranker_model or config.RERANKER_MODEL
        )

        # Initialize generator with config defaults
        generator_api_key = config.GROQ_API_KEY if effective_provider == 'groq' else config.OPENAI_API_KEY
        self.generator = ResponseGenerator(
            api_key=generator_api_key,
            provider=effective_provider,
            model=llm_model or config.LLM_MODEL
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
                    'text': c.get('text', ''),
                    'source_url': c.get('source_url', ''),
                    'master_context': c.get('master_context', ''),
                    'document_context': c.get('document_context', ''),
                    'chunk_context': c.get('chunk_context', '')
                }
                for c in retrieved_chunks
            ]

            # Collect unique document contexts for display
            doc_contexts = {}
            for c in retrieved_chunks:
                filename = c.get('filename', '')
                doc_context = c.get('document_context', '')
                if filename and doc_context and filename not in doc_contexts:
                    doc_contexts[filename] = doc_context
            debug_data['document_contexts'] = doc_contexts

            # Store master context (same for all chunks, just grab from first)
            if retrieved_chunks:
                debug_data['master_context'] = retrieved_chunks[0].get('master_context', '')

        # Step 2: Rerank
        if self.reranker:
            # Use adaptive mode from config
            adaptive_mode = getattr(config, 'RERANK_ADAPTIVE_MODE', False)

            if debug:
                reranked_chunks, reranker_debug = self.reranker.rerank(
                    query, retrieved_chunks,
                    top_k=config.RERANK_TOP_K,
                    adaptive=adaptive_mode,
                    debug=True
                )
                debug_data['reranker_scores'] = reranker_debug.get('raw_scores', {})
                debug_data['reranker_prompt'] = reranker_debug.get('reranker_prompt', '')
                debug_data['reranker_reasoning'] = reranker_debug.get('reranker_reasoning', 'No reasoning captured')

                # Add adaptive selection info if available
                if 'adaptive_selection' in reranker_debug:
                    debug_data['adaptive_selection'] = reranker_debug['adaptive_selection']
            else:
                reranked_chunks = self.reranker.rerank(
                    query, retrieved_chunks,
                    top_k=config.RERANK_TOP_K,
                    adaptive=adaptive_mode
                )
        else:
            reranked_chunks = retrieved_chunks[:config.RERANK_TOP_K]

        # Store final chunks for debug
        if debug:
            debug_data['final_chunks'] = [
                {
                    'doc': c.get('filename', ''),
                    'page': c.get('page', ''),
                    'text': c.get('text', ''),
                    'source_url': c.get('source_url', ''),
                    'chunk_context': c.get('chunk_context', ''),
                    'final_score': c.get('final_score', 0)
                }
                for c in reranked_chunks
            ]

            # Track which chunks passed/failed reranking
            # Reranked chunks have the top_k highest scores
            final_chunk_indices = set()
            for idx, c in enumerate(reranked_chunks):
                # Find the index of this chunk in the original retrieved_chunks
                matched = False
                for i, orig in enumerate(retrieved_chunks):
                    if orig.get('text') == c.get('text'):
                        final_chunk_indices.add(i)
                        matched = True
                        break
                if not matched:
                    print(f"[DEBUG] Reranked chunk {idx} (score={c.get('final_score')}) did not match any retrieved chunk")
                    print(f"[DEBUG] Text preview: {c.get('text', '')[:100]}...")
                    print(f"[DEBUG] Has text key: {'text' in c}, text is None: {c.get('text') is None}")

            debug_data['reranker_threshold'] = {
                'total_retrieved': len(retrieved_chunks),
                'passed_count': len(final_chunk_indices),  # Use actual matched count, not requested count
                'failed_count': len(retrieved_chunks) - len(final_chunk_indices),
                'passed_indices': sorted(list(final_chunk_indices)),
                'cutoff_score': reranked_chunks[-1].get('final_score', 0) if reranked_chunks else 0
            }

        # Step 3: Generate
        result = self.generator.generate(query, reranked_chunks)

        # Step 4: Format response
        # Extract cited sources (deduplicated by doc+page)
        cited_sources = extract_cited_sources(result['answer'], reranked_chunks)

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
