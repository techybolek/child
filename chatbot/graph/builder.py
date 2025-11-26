"""Graph construction for LangGraph RAG pipeline"""

from langgraph.graph import StateGraph, END

from .state import RAGState
from .nodes.classify import classify_node
from .nodes.retrieve import retrieve_node
from .nodes.rerank import rerank_node
from .nodes.generate import generate_node
from .nodes.location import location_node
from .edges import route_by_intent


def build_rag_graph():
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


# Singleton graph instance
_graph = None


def get_graph():
    """Get or create the RAG graph (singleton pattern).

    Returns:
        Compiled LangGraph workflow
    """
    global _graph
    if _graph is None:
        _graph = build_rag_graph()
    return _graph
