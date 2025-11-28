"""State definition for LangGraph RAG pipeline"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


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


class ConversationalRAGState(TypedDict):
    """State for conversational RAG pipeline with memory.

    Extends RAGState with conversation history for multi-turn interactions.
    The messages field uses add_messages reducer to accumulate conversation.
    """

    # Conversation history (accumulated via add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # Current turn
    query: str                                      # Original user query
    reformulated_query: str | None                  # History-aware query (Milestone 2)

    # Routing
    intent: Literal["information", "location_search"] | None

    # Retrieval
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]

    # Output
    answer: str | None
    sources: list[dict]
    response_type: str
    action_items: list[dict]

    # Debug
    debug: bool
    debug_info: dict | None
