"""Query reformulation node for conversational RAG pipeline.

Transforms context-dependent follow-up queries into standalone queries
that can be used for retrieval without losing conversation context.
"""

import re
from openai import OpenAI
from groq import Groq
from langchain_core.messages import HumanMessage, AIMessage

from ... import config
from ...prompts.conversational.reformulation_prompt import (
    REFORMULATION_SYSTEM,
    REFORMULATION_USER,
)


def format_conversation_history(messages: list, max_turns: int = 5) -> str:
    """Format message history for prompt injection.

    Args:
        messages: List of BaseMessage objects
        max_turns: Maximum number of recent turns to include

    Returns:
        Formatted conversation string
    """
    if not messages:
        return ""

    # Take last N turns (each turn = 1 user + 1 assistant message)
    recent = messages[-(max_turns * 2):]

    lines = []
    for msg in recent:
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Truncate long assistant responses
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"Assistant: {content}")

    return "\n".join(lines)


def extract_reformulated_query(response_text: str) -> str | None:
    """Extract reformulated query from LLM response.

    Handles both XML tag format and plain text response.

    Args:
        response_text: Raw LLM response

    Returns:
        Extracted query or None if extraction fails
    """
    # Try XML tag extraction first
    match = re.search(r"<reformulated_query>(.*?)(?:</reformulated_query>|$)", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: if response starts with the tag content (no closing tag)
    if response_text.strip():
        return response_text.strip()

    return None


def needs_reformulation(query: str) -> bool:
    """Quick check if query likely needs reformulation.

    Queries with pronouns or implicit references need reformulation.
    Standalone queries can skip the LLM call.

    Args:
        query: User's query

    Returns:
        True if query likely needs reformulation
    """
    # EXISTING: Patterns that indicate context dependency
    context_markers = [
        r"\b(it|its|they|them|their|this|that|these|those)\b",
        r"\b(what about|how about|and|also|too)\b",
        r"^\s*(same|similar|like that|more|else)\b",
        r"^(can|could|would|is|are|do|does|did)\s+(it|they|that|this)\b",
    ]

    # NEW: Correction patterns
    correction_patterns = [
        r"\b(i meant|sorry|actually|no,?\s*i|correction)\b",
        r"\b(i said|i was asking|not \d+)\b",
    ]

    # NEW: Topic return patterns
    topic_return_patterns = [
        r"\b(back to|return to|going back|earlier|previous)\b",
        r"\b(my .* question|as i (asked|said)|originally)\b",
    ]

    # NEW: Hypothetical/scenario patterns
    hypothetical_patterns = [
        r"\b(what if|suppose|assuming|if i|if my)\b",
        r"\b(raise to|increase to|goes? up|changed? to)\b",
    ]

    # NEW: Negation with carryover
    negation_carryover_patterns = [
        r"^which (ones?|programs?) (don't|aren't|do not|are not)\b",
        r"^(the ones?|those) (that )?(don't|aren't)\b",
    ]

    all_patterns = (
        context_markers +
        correction_patterns +
        topic_return_patterns +
        hypothetical_patterns +
        negation_carryover_patterns
    )

    query_lower = query.lower()
    for pattern in all_patterns:
        if re.search(pattern, query_lower):
            return True

    # Very short queries often need context
    if len(query.split()) <= 3:
        return True

    return False


def reformulate_node(state: dict) -> dict:
    """Reformulate query using conversation history.

    If no history exists or query is already standalone,
    returns the original query unchanged.

    Args:
        state: ConversationalRAGState with 'query' and 'messages' fields

    Returns:
        dict with 'reformulated_query' field
    """
    query = state["query"]
    messages = state.get("messages", [])

    # If no conversation history, use original query
    # (first message is the current query, so we need > 1)
    if len(messages) <= 1:
        print(f"[Reformulate Node] No history, using original query")
        return {"reformulated_query": query}

    # Quick check: does this query need reformulation?
    if not needs_reformulation(query):
        print(f"[Reformulate Node] Query appears standalone, skipping reformulation")
        return {"reformulated_query": query}

    # Get history (exclude current message which is the last one)
    history = format_conversation_history(messages[:-1])

    if not history:
        print(f"[Reformulate Node] Empty history after formatting, using original query")
        return {"reformulated_query": query}

    print(f"[Reformulate Node] Reformulating query with {len(messages)-1} previous messages")

    # Check for overrides in state, fall back to reformulator-specific config
    provider = state.get("reformulator_provider_override") or config.REFORMULATOR_PROVIDER
    model = state.get("reformulator_model_override") or config.REFORMULATOR_MODEL

    # Initialize client based on provider
    if provider == 'groq':
        client = Groq(api_key=config.GROQ_API_KEY)
    else:
        client = OpenAI(api_key=config.OPENAI_API_KEY)

    prompt = REFORMULATION_USER.format(history=history, query=query)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": REFORMULATION_SYSTEM},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            seed=config.SEED,
            max_tokens=300,
        )

        content = response.choices[0].message.content
        if content is None:
            print(f"[Reformulate Node] WARNING: Empty response, using original query")
            return {"reformulated_query": query}

        reformulated = extract_reformulated_query(content)

        if reformulated and reformulated != query:
            print(f"[Reformulate Node] Original: {query}")
            print(f"[Reformulate Node] Reformulated: {reformulated}")
            return {"reformulated_query": reformulated}
        else:
            print(f"[Reformulate Node] No change needed")
            return {"reformulated_query": query}

    except Exception as e:
        print(f"[Reformulate Node] ERROR: {type(e).__name__}: {str(e)}")
        print(f"[Reformulate Node] Falling back to original query")
        return {"reformulated_query": query}
