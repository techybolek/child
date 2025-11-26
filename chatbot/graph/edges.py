"""Conditional routing logic for LangGraph RAG pipeline"""

from typing import Literal


def route_by_intent(state: dict) -> Literal["retrieve", "location"]:
    """Route to appropriate path based on classified intent.

    Args:
        state: RAGState with 'intent' field

    Returns:
        "retrieve" for information queries (RAG path)
        "location" for location search queries (template path)
    """
    intent = state.get("intent")

    if intent == "location_search":
        print("[Router] Routing to location path")
        return "location"
    else:
        print("[Router] Routing to retrieve path (information)")
        return "retrieve"
