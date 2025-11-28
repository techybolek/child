"""Query reformulation prompt for conversational context resolution.

Transforms context-dependent follow-up queries into standalone queries for retrieval.
"""

REFORMULATION_SYSTEM = """You reformulate follow-up questions into standalone queries for a Texas childcare assistance chatbot.

<domain>
Texas childcare programs: CCS (Child Care Services), CCMS, Texas Rising Star, PSOC (Parent Share of Cost).
Key concepts: SMI (State Median Income), income eligibility, workforce boards, BCY (Biennial Contract Year).
</domain>"""

REFORMULATION_USER = """<conversation>
{history}
</conversation>

<current_query>{query}</current_query>

Reformulate the current query to be standalone. If already standalone, return unchanged.

<reformulated_query>"""

# Examples for few-shot (can be injected when confidence is low)
REFORMULATION_EXAMPLES = [
    {
        "history": "User: What is the income limit for CCS?\nAssistant: The income limit is 85% of SMI...",
        "query": "What about for a family of 4?",
        "reformulated": "What is the income limit for CCS for a family of 4?"
    },
    {
        "history": "User: Tell me about CCMS\nAssistant: CCMS is the Child Care Management Services...",
        "query": "How do I apply?",
        "reformulated": "How do I apply for the Child Care Management Services (CCMS) program?"
    },
    {
        "history": "User: I have 2 kids and make $3000/month\nAssistant: Based on that income...",
        "query": "Am I eligible?",
        "reformulated": "Is a family with 2 children and monthly income of $3000 eligible for Texas childcare assistance?"
    },
    {
        "history": "",
        "query": "What are the income limits?",
        "reformulated": "What are the income limits?"  # Already standalone
    }
]
