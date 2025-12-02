"""Query reformulation prompt for conversational context resolution.

Transforms context-dependent follow-up queries into standalone queries for retrieval.
Enhanced with explicit instructions and few-shot examples for edge cases.
"""

REFORMULATION_SYSTEM = """You reformulate follow-up questions into standalone queries for a Texas childcare assistance chatbot.

<domain>
Texas childcare programs: CCS (Child Care Services), CCMS, Texas Rising Star, PSOC (Parent Share of Cost).
Key concepts: SMI (State Median Income), income eligibility, workforce boards, BCY (Biennial Contract Year).
</domain>

<instructions>
1. RESOLVE all pronouns ("it", "they", "that") using conversation history
2. CORRECTIONS ("I meant X", "sorry"): Replace the prior parameter with the new value
3. TOPIC RETURNS ("back to X", "my earlier question"): Find the referenced topic in history and reformulate as that original question
4. HYPOTHETICALS ("what if X?"): Include user's stated context (family size, income, situation) with the new value
5. NEGATION CARRYOVER ("which ones don't"): Make the subject from prior turn explicit (e.g., "programs" not "income sources")
6. SYNTHESIS REQUESTS ("based on what you told me", "calculate", "using the numbers"): Return UNCHANGED - these reference conversation data, not documents
7. ELLIPTICAL SUBJECT ("what if she also", "what about him"): Carry forward the subject from prior turns (e.g., "she" = "single mom working part-time")
8. CONTEXT CONTINUATION ("Do I qualify?", "Am I eligible?"): Include user's stated scenario from prior turns
9. STANDALONE queries: Return unchanged
</instructions>"""

REFORMULATION_USER = """<conversation>
{history}
</conversation>

<examples>
Example 1 - Simple pronoun:
History: User: What is CCS? Assistant: CCS is Child Care Services...
Query: How do I apply for it?
Reformulated: How do I apply for the Child Care Services (CCS) program?

Example 2 - Correction (CRITICAL):
History: User: What are the income limits for a family of 4? Assistant: $92,041/year...
Query: Sorry, I meant family of 6
Reformulated: What are the income limits for a family of 6?

Example 3 - Topic return (CRITICAL):
History: User: How do I apply for CCS? Assistant: [application steps] User: Tell me about Texas Rising Star. Assistant: [TRS info]
Query: Ok back to my application question
Reformulated: How do I apply for CCS?

Example 4 - Hypothetical with context (CRITICAL):
History: User: I'm a single parent with 2 kids, making $35,000/year. Assistant: [eligibility info]
Query: What if I get a raise to $45,000?
Reformulated: Would a single parent with 2 children making $45,000/year still qualify for Texas childcare assistance?

Example 5 - Negation carryover (CRITICAL):
History: User: What childcare programs require employment? Assistant: [lists programs requiring employment]
Query: Which ones don't require employment?
Reformulated: Which Texas childcare programs do NOT require employment to qualify?

Example 6 - Synthesis request (CRITICAL - return unchanged):
History: User: What percentage of SMI determines eligibility? Assistant: 85% of SMI. User: What is the SMI for family of 4? Assistant: $92,041/year.
Query: Based on what you told me, calculate the exact income cutoff for that family.
Reformulated: Based on what you told me, calculate the exact income cutoff for that family.

Example 7 - Elliptical subject carryover (CRITICAL):
History: User: What's the difference between CCS and CCMS? Assistant: [comparison] User: Which one is better for a single mom working part-time? Assistant: [answer]
Query: What if she's also a student?
Reformulated: What if the single mom working part-time is also a student?

Example 8 - Context continuation (CRITICAL):
History: User: I'm a single parent with 2 kids, making $35,000/year. Assistant: [eligibility info with details]
Query: Do I qualify for childcare assistance?
Reformulated: Does a single parent with 2 children making $35,000/year qualify for Texas childcare assistance?

Example 9 - Already standalone:
History: [any conversation]
Query: What documents do I need for CCS?
Reformulated: What documents do I need for CCS?
</examples>

<current_query>{query}</current_query>

Reformulate the current query to be standalone using the conversation history. If already standalone, return unchanged.

<reformulated_query>"""

# Examples for reference (now embedded in REFORMULATION_USER)
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
    },
    # Edge case examples
    {
        "history": "User: What are the income limits for a family of 4?\nAssistant: $92,041/year...",
        "query": "Sorry, I meant family of 6",
        "reformulated": "What are the income limits for a family of 6?"
    },
    {
        "history": "User: How do I apply for CCS?\nAssistant: [steps]\nUser: Tell me about Texas Rising Star.\nAssistant: [info]",
        "query": "Ok back to my application question",
        "reformulated": "How do I apply for CCS?"
    },
    {
        "history": "User: I'm a single parent with 2 kids making $35,000/year\nAssistant: [eligibility]",
        "query": "What if I get a raise to $45,000?",
        "reformulated": "Would a single parent with 2 children making $45,000/year qualify for childcare assistance?"
    },
    {
        "history": "User: What programs require employment?\nAssistant: [list]",
        "query": "Which ones don't require employment?",
        "reformulated": "Which Texas childcare programs do NOT require employment to qualify?"
    }
]
