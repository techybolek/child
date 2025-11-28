"""Location search node for LangGraph RAG pipeline"""

from ...prompts import LOCATION_SEARCH_TEMPLATE


def location_node(state: dict) -> dict:
    """Return template response for location queries.

    Returns a pre-defined template directing users to the
    Texas HHS childcare facility search tool.

    Args:
        state: RAGState (query field ignored for template response)

    Returns:
        dict with 'answer', 'sources', 'response_type', 'action_items'
    """
    print("[Location Node] Returning location search template")

    result = {
        "answer": LOCATION_SEARCH_TEMPLATE,
        "sources": [],
        "response_type": "location_search",
        "action_items": [
            {
                'type': 'link',
                'url': 'https://childcare.hhs.texas.gov/Public/ChildCareSearch',
                'label': 'Search for Childcare Facilities',
                'description': 'Official Texas HHS facility search tool'
            }
        ]
    }

    # If conversational mode, append AI message for memory
    if "messages" in state:
        from langchain_core.messages import AIMessage
        result["messages"] = [AIMessage(content=LOCATION_SEARCH_TEMPLATE)]

    return result
