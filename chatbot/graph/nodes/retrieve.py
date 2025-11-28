"""Retrieval node for LangGraph RAG pipeline"""

from ... import config
from ...retriever import QdrantRetriever
from ...hybrid_retriever import QdrantHybridRetriever


def retrieve_node(state: dict) -> dict:
    """Retrieve chunks from Qdrant vector database.

    Selects retriever based on config.RETRIEVAL_MODE:
    - 'hybrid': Dense + sparse with RRF fusion
    - 'dense': Dense-only semantic search

    Uses reformulated_query if available (conversational mode),
    otherwise falls back to original query.

    Args:
        state: RAGState with 'query', optional 'reformulated_query' and 'debug' fields

    Returns:
        dict with 'retrieved_chunks' and optionally updated 'debug_info'
    """
    # Use reformulated query if available (conversational mode)
    query = state.get("reformulated_query") or state["query"]
    debug = state.get("debug", False)

    # Select retriever based on config
    if config.RETRIEVAL_MODE == 'hybrid':
        retriever = QdrantHybridRetriever()
        print(f"[Retrieve Node] Using hybrid retriever (dense + sparse RRF)")
    else:
        retriever = QdrantRetriever()
        print(f"[Retrieve Node] Using dense retriever")

    # Retrieve chunks
    chunks = retriever.search(query, top_k=config.RETRIEVAL_TOP_K)
    print(f"[Retrieve Node] Retrieved {len(chunks)} chunks")

    # Build result
    result = {"retrieved_chunks": chunks}

    # Add debug info if requested
    if debug:
        debug_info = state.get("debug_info") or {}
        debug_info["retrieved_chunks"] = [
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
            for c in chunks
        ]

        # Collect unique document contexts
        doc_contexts = {}
        for c in chunks:
            filename = c.get('filename', '')
            doc_context = c.get('document_context', '')
            if filename and doc_context and filename not in doc_contexts:
                doc_contexts[filename] = doc_context
        debug_info['document_contexts'] = doc_contexts

        # Store master context (same for all chunks)
        if chunks:
            debug_info['master_context'] = chunks[0].get('master_context', '')

        result["debug_info"] = debug_info

    return result
