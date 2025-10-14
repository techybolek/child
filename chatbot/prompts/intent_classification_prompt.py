"""Intent classification prompt for routing user queries"""

INTENT_CLASSIFICATION_PROMPT = """Classify this user query into ONE category:

Categories:
- location_search: User wants to FIND or SEARCH for childcare facilities/providers near a location (e.g., "find daycare near me", "search for providers in Austin", "where can I find childcare")
- information: User wants INFORMATION about policies, eligibility, programs, requirements, income limits, application process, etc.

Rules:
- If query mentions "find", "search", "near", "location", or "where can I" "show schools" or "near me" → location_search
- If query asks "what", "how", "who qualifies", "income limits", "requirements" → information
- Default to information if uncertain

Query: "{query}"

Respond with ONLY the category name (location_search or information):"""
