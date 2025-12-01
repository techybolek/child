"""Generation node for LangGraph RAG pipeline"""

import re
from ... import config
from ...generator import ResponseGenerator


def generate_node(state: dict) -> dict:
    """Generate answer from reranked chunks.

    Uses ResponseGenerator to create an answer with citations,
    then extracts the cited sources.
    Uses reformulated_query if available (conversational mode),
    otherwise falls back to original query.

    Args:
        state: RAGState with 'query', optional 'reformulated_query', and 'reranked_chunks' fields

    Returns:
        dict with 'answer', 'sources', 'response_type', 'action_items'
    """
    # Use reformulated query if available (conversational mode)
    query = state.get("reformulated_query") or state["query"]
    reranked_chunks = state["reranked_chunks"]

    # Handle empty chunks
    if not reranked_chunks:
        print("[Generate Node] No chunks available, returning fallback response")
        return {
            "answer": "I couldn't find information about that. Try calling 1-800-862-5252.",
            "sources": [],
            "response_type": "information",
            "action_items": []
        }

    # Check for overrides in state, fall back to config
    provider = state.get("provider_override") or config.LLM_PROVIDER
    model = state.get("llm_model_override") or config.LLM_MODEL

    # Initialize generator
    api_key = config.GROQ_API_KEY if provider == 'groq' else config.OPENAI_API_KEY
    generator = ResponseGenerator(
        api_key=api_key,
        provider=provider,
        model=model
    )

    print(f"[Generate Node] Generating answer with {model}")

    # Generate response
    result = generator.generate(query, reranked_chunks)
    answer = result['answer']

    # Extract cited sources (same logic as RAGHandler._extract_cited_sources)
    cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+)\]', answer))
    sources = []
    for doc_num in sorted(cited_doc_nums, key=int):
        idx = int(doc_num) - 1  # Convert to 0-based index
        if 0 <= idx < len(reranked_chunks):
            chunk = reranked_chunks[idx]
            sources.append({
                'doc': chunk['filename'],
                'page': chunk['page'],
                'url': chunk['source_url']
            })

    print(f"[Generate Node] Generated answer with {len(sources)} cited sources")

    result = {
        "answer": answer,
        "sources": sources,
        "response_type": "information",
        "action_items": []
    }

    # If conversational mode, append AI message for memory
    if "messages" in state:
        from langchain_core.messages import AIMessage
        result["messages"] = [AIMessage(content=answer)]

    return result
