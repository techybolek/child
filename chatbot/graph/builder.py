"""Graph construction for LangGraph RAG pipeline"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from chatbot import config
from .state import RAGState, ConversationalRAGState
from .nodes.classify import classify_node
from .nodes.retrieve import retrieve_node
from .nodes.rerank import rerank_node
from .nodes.generate import generate_node
from .nodes.location import location_node
from .edges import route_by_intent


def build_graph(checkpointer=None):
    """Build RAG graph - stateless or conversational based on config.

    Args:
        checkpointer: Optional checkpointer for conversation memory.
                      Only used when CONVERSATIONAL_MODE=True.

    Returns:
        Compiled LangGraph workflow
    """
    if config.CONVERSATIONAL_MODE:
        return _build_conversational_graph(checkpointer)
    else:
        return _build_stateless_graph()


def _build_stateless_graph():
    """Build the stateless RAG graph.

    Graph structure:
        START → CLASSIFY → [conditional]
                              ├── RETRIEVE → RERANK → GENERATE → END
                              └── LOCATION → END

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(RAGState)

    # Add nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)

    # Entry point
    workflow.set_entry_point("classify")

    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "location": "location"
        }
    )

    # Information path: retrieve → rerank → generate → END
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)

    # Location path: location → END
    workflow.add_edge("location", END)

    # Compile (no checkpointer = stateless)
    print("[Graph Builder] Building stateless RAG graph")
    return workflow.compile()


def _build_conversational_graph(checkpointer=None):
    """Build conversational RAG graph with memory.

    Graph structure (same as stateless for Milestone 1):
        START → CLASSIFY → [conditional]
                              ├── RETRIEVE → RERANK → GENERATE → END
                              └── LOCATION → END

    Args:
        checkpointer: Checkpointer for conversation memory.
                      Defaults to MemorySaver if not provided.

    Returns:
        Compiled LangGraph workflow with memory
    """
    workflow = StateGraph(ConversationalRAGState)

    # Same nodes as stateless
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("location", location_node)

    # Entry point
    workflow.set_entry_point("classify")

    # Conditional routing after classification
    workflow.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "retrieve": "retrieve",
            "location": "location"
        }
    )

    # Information path: retrieve → rerank → generate → END
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", END)

    # Location path: location → END
    workflow.add_edge("location", END)

    # Use default checkpointer if not provided
    if checkpointer is None:
        checkpointer = MemorySaver()

    print("[Graph Builder] Building conversational RAG graph with memory")
    return workflow.compile(checkpointer=checkpointer)


# Legacy function for backward compatibility
def build_rag_graph():
    """Build the stateless RAG graph (legacy function).

    Deprecated: Use build_graph() instead.
    """
    return _build_stateless_graph()


# Singleton graph instance
_graph = None


def get_graph():
    """Get or create the RAG graph (singleton pattern).

    Returns:
        Compiled LangGraph workflow
    """
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
