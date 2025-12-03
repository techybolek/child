"""Generation node for LangGraph RAG pipeline"""

import re
from langchain_core.messages import HumanMessage, AIMessage
from ... import config
from ...generator import ResponseGenerator


def _format_recent_history(messages: list, max_turns: int) -> str:
    """Format last N Q&A pairs from conversation history.

    Extracts the most recent Q&A pairs (excluding the current query) for
    entity reference resolution and multi-hop reasoning.

    Args:
        messages: List of LangChain message objects (HumanMessage, AIMessage)
        max_turns: Maximum number of Q&A pairs to include

    Returns:
        Formatted string of recent Q&A pairs, or empty string if no history
    """
    if not messages or len(messages) < 2:
        return ""

    # Skip the last message (current query) and work backwards
    # We want completed Q&A pairs only
    history_messages = messages[:-1]

    # Extract pairs: we need HumanMessage followed by AIMessage
    pairs = []
    i = 0
    while i < len(history_messages) - 1:
        if isinstance(history_messages[i], HumanMessage) and isinstance(history_messages[i + 1], AIMessage):
            human_content = history_messages[i].content
            ai_content = history_messages[i + 1].content
            # Truncate long responses to avoid token bloat
            if len(ai_content) > 500:
                ai_content = ai_content[:500] + "..."
            pairs.append(f"Q: {human_content}\nA: {ai_content}")
            i += 2
        else:
            i += 1

    if not pairs:
        return ""

    # Take last N pairs
    recent_pairs = pairs[-max_turns:]

    return "\n\n".join(recent_pairs)


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

    # Extract recent history for conversational mode (for multi-hop reasoning)
    recent_history = None
    if "messages" in state and state["messages"]:
        recent_history = _format_recent_history(
            state["messages"],
            config.GENERATOR_HISTORY_TURNS
        )
        if recent_history:
            print(f"[Generate Node] Injecting {len(recent_history)} chars of conversation history")

    # Generate response
    result = generator.generate(query, reranked_chunks, recent_history=recent_history)
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
