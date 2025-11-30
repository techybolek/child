"""Reranking node for LangGraph RAG pipeline"""

from ... import config
from ...reranker import LLMJudgeReranker


def rerank_node(state: dict) -> dict:
    """Rerank chunks using LLM judge scoring.

    Uses the same adaptive reranking logic as RAGHandler.
    Uses reformulated_query if available (conversational mode),
    otherwise falls back to original query.

    Args:
        state: RAGState with 'query', optional 'reformulated_query', 'retrieved_chunks', and 'debug' fields

    Returns:
        dict with 'reranked_chunks' and optionally updated 'debug_info'
    """
    # Use reformulated query if available (conversational mode)
    query = state.get("reformulated_query") or state["query"]
    retrieved_chunks = state["retrieved_chunks"]
    debug = state.get("debug", False)

    # Handle empty retrieval
    if not retrieved_chunks:
        print("[Rerank Node] No chunks to rerank")
        return {"reranked_chunks": []}

    # Initialize reranker
    provider = config.LLM_PROVIDER
    api_key = config.GROQ_API_KEY if provider == 'groq' else config.OPENAI_API_KEY
    reranker = LLMJudgeReranker(
        api_key=api_key,
        provider=provider,
        model=config.RERANKER_MODEL
    )

    print(f"[Rerank Node] Reranking {len(retrieved_chunks)} chunks with {config.RERANKER_MODEL}")

    # Use adaptive mode from config
    adaptive_mode = getattr(config, 'RERANK_ADAPTIVE_MODE', False)

    # Build result
    result = {}

    if debug:
        reranked_chunks, reranker_debug = reranker.rerank(
            query, retrieved_chunks,
            top_k=config.RERANK_TOP_K,
            adaptive=adaptive_mode,
            debug=True
        )

        debug_info = state.get("debug_info") or {}
        debug_info['reranker_scores'] = reranker_debug.get('raw_scores', {})
        debug_info['reranker_prompt'] = reranker_debug.get('reranker_prompt', '')
        debug_info['reranker_reasoning'] = reranker_debug.get('reranker_reasoning', 'No reasoning captured')

        if 'adaptive_selection' in reranker_debug:
            debug_info['adaptive_selection'] = reranker_debug['adaptive_selection']

        # Track final chunks
        debug_info['final_chunks'] = [
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

        # Track reranker threshold info
        final_chunk_indices = set()
        for c in reranked_chunks:
            for i, orig in enumerate(retrieved_chunks):
                if orig.get('text') == c.get('text'):
                    final_chunk_indices.add(i)
                    break

        debug_info['reranker_threshold'] = {
            'total_retrieved': len(retrieved_chunks),
            'passed_count': len(final_chunk_indices),
            'failed_count': len(retrieved_chunks) - len(final_chunk_indices),
            'passed_indices': sorted(list(final_chunk_indices)),
            'cutoff_score': reranked_chunks[-1].get('final_score', 0) if reranked_chunks else 0
        }

        result["reranked_chunks"] = reranked_chunks
        result["debug_info"] = debug_info
    else:
        reranked_chunks = reranker.rerank(
            query, retrieved_chunks,
            top_k=config.RERANK_TOP_K,
            adaptive=adaptive_mode
        )
        result["reranked_chunks"] = reranked_chunks

    print(f"[Rerank Node] Selected {len(result['reranked_chunks'])} chunks after reranking")
    return result
