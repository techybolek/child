"""Visualization utility for RAG pipeline graph"""

from .builder import get_graph


def to_mermaid() -> str:
    """Export graph as Mermaid diagram string"""
    graph = get_graph()
    return graph.get_graph().draw_mermaid()


if __name__ == "__main__":
    print(to_mermaid())
