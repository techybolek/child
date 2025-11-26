"""State definition for LangGraph RAG pipeline"""

from typing import TypedDict, Literal


class RAGState(TypedDict):
    """State for RAG pipeline graph.

    This state flows through the graph nodes, accumulating data
    at each step. The graph is stateless (no conversation memory).
    """

    # Input
    query: str                              # User's question
    debug: bool                             # Enable debug output

    # Routing
    intent: Literal["information", "location_search"] | None

    # Retrieval (information path)
    retrieved_chunks: list[dict]            # From Qdrant
    reranked_chunks: list[dict]             # After LLM scoring

    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]
    debug_info: dict | None
