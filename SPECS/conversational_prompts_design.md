# Conversational RAG Prompts Design

Prompt specifications for the conversational RAG pipeline. All prompts follow modern best practices.

## Design Principles

1. **Structured Output** - Use XML tags or JSON schemas for predictable parsing
2. **Minimal Instructions** - Let examples do the teaching, not verbose rules
3. **Domain Context First** - Lead with domain knowledge, not task mechanics
4. **Single Responsibility** - Each prompt does one thing well
5. **Fail-Safe Defaults** - Graceful handling of edge cases

---

## Prompt 1: Query Reformulation

**Purpose:** Transform context-dependent follow-up queries into standalone queries for retrieval.

**File:** `chatbot/prompts/conversational/reformulation_prompt.py`

```python
"""Query reformulation prompt for conversational context resolution."""

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

# Examples for few-shot (injected when confidence is low)
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
```

**Design Notes:**
- System prompt establishes domain context upfront
- User prompt uses XML tags for clear structure
- Examples show the pattern, not rules
- Handles "already standalone" case explicitly
- No verbose instructions - examples teach the behavior

---

## Prompt 2: Intent Classification (Updated)

**Purpose:** Classify user intent, now using reformulated query.

**File:** `chatbot/prompts/conversational/intent_classification_prompt.py`

```python
"""Intent classification prompt for routing - conversational version."""

INTENT_CLASSIFICATION_PROMPT = """Classify this query about Texas childcare assistance.

<query>{query}</query>

<categories>
information: Policy, eligibility, programs, requirements, income limits, how-to questions
location_search: Finding childcare facilities/providers near a location
</categories>

<output>category_name</output>"""
```

**Design Notes:**
- Removed verbose rules - categories are self-explanatory
- Single XML block for output format
- Uses `reformulated_query` as input (handled in node, not prompt)
- Dropped `clarification` intent for v1 simplicity

---

## Prompt 3: Reranking (Conversation-Aware)

**Purpose:** Score chunk relevance with optional conversation context.

**File:** `chatbot/prompts/conversational/reranking_prompt.py`

```python
"""Reranking prompt with optional conversation context."""

RERANKING_PROMPT = """Score these chunks for relevance to the question.

<question>{query}</question>

{chunks_xml}

<scoring>
9-10: Direct answer with specific data
7-8: Highly relevant, addresses main aspects  
5-6: Partial relevance, incomplete for question
3-4: Related topic, wrong specifics (year, category)
1-2: Tangential connection
0: Unrelated
</scoring>

<scores>{{"chunk_0": N, "chunk_1": N, ...}}</scores>"""

# Conversation-aware variant (used when history exists)
RERANKING_PROMPT_CONVERSATIONAL = """Score these chunks for relevance to the question in context.

<conversation_summary>{conversation_summary}</conversation_summary>

<question>{query}</question>

{chunks_xml}

<scoring>
9-10: Direct answer with specific data
7-8: Highly relevant, addresses main aspects  
5-6: Partial relevance, incomplete for question
3-4: Related topic, wrong specifics (year, category)
1-2: Tangential connection
0: Unrelated
</scoring>

Consider conversation context when entities are ambiguous.

<scores>{{"chunk_0": N, "chunk_1": N, ...}}</scores>"""


def format_chunks_xml(chunks: list[dict]) -> str:
    """Format chunks as XML for prompt injection."""
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f'<chunk id="{i}">\n{chunk["text"]}\n</chunk>')
    return "\n".join(parts)
```

**Design Notes:**
- Two variants: stateless and conversational
- XML structure for chunks (better than numbered lists)
- Scoring guide is compact, not verbose
- Helper function for consistent chunk formatting

---

## Prompt 4: Response Generation (Conversation-Aware)

**Purpose:** Generate answers with citations, aware of conversation history.

**File:** `chatbot/prompts/conversational/response_generation_prompt.py`

```python
"""Response generation prompt - conversational version."""

RESPONSE_GENERATION_SYSTEM = """You are an expert on Texas childcare assistance programs.

<abbreviations>
{abbreviations}
</abbreviations>

<rules>
- Cite sources as [Doc X]
- State exact amounts with year/BCY
- Say "I don't have information on..." if missing
- Never invent numbers or dates
</rules>"""

RESPONSE_GENERATION_USER = """<documents>
{context}
</documents>

<question>{query}</question>

<answer>"""

# Conversational variant includes history summary
RESPONSE_GENERATION_USER_CONVERSATIONAL = """<conversation_context>
{conversation_summary}
</conversation_context>

<documents>
{context}
</documents>

<question>{query}</question>

Maintain consistency with previous answers. Reference prior discussion if relevant.

<answer>"""
```

**Design Notes:**
- System/user split for chat models
- Abbreviations injected into system prompt
- Conversational variant adds context summary
- Instruction to maintain consistency across turns

---

## Prompt 5: Multi-Turn Judge

**Purpose:** Evaluate chatbot responses in multi-turn context for testing.

**File:** `evaluation/prompts/multi_turn_judge_prompt.py`

```python
"""Multi-turn conversation judge prompt."""

MULTI_TURN_JUDGE_PROMPT = """Evaluate this chatbot response in a multi-turn conversation.

<conversation>
{conversation_history}
</conversation>

<current_turn>
<original_query>{original_query}</original_query>
<reformulated_query>{reformulated_query}</reformulated_query>
<response>{response}</response>
</current_turn>

<expected>
<topics>{expected_topics}</topics>
<must_contain>{expected_contains}</must_contain>
<requires_context>{requires_context}</requires_context>
</expected>

<criteria>
accuracy (0-5): Factual correctness for Texas childcare policies
completeness (0-5): Addresses the question including context from history
context_resolution (0-5): Correctly interprets references to prior turns
coherence (0-3): Clear, natural, well-structured
</criteria>

<evaluation>
{{
  "accuracy": N,
  "accuracy_reasoning": "...",
  "completeness": N,
  "completeness_reasoning": "...",
  "context_resolution": N,
  "context_reasoning": "...",
  "coherence": N,
  "coherence_reasoning": "..."
}}
</evaluation>"""
```

**Design Notes:**
- XML structure throughout for parsing reliability
- Explicit separation of original vs reformulated query
- Context resolution as dedicated scoring dimension
- JSON output inside XML tags (hybrid approach works well)

---

## Prompt 6: Conversation Summarizer

**Purpose:** Summarize conversation history for context injection (keeps prompts compact).

**File:** `chatbot/prompts/conversational/summarizer_prompt.py`

```python
"""Conversation summarizer for context compression."""

SUMMARIZER_PROMPT = """Summarize this conversation for context injection.

<conversation>
{messages}
</conversation>

Extract:
- Key entities (programs, amounts, family details)
- Decisions/conclusions reached
- Open questions

<summary max_tokens="150">"""
```

**Design Notes:**
- Used when conversation exceeds N turns
- Extracts only retrieval-relevant context
- Token limit prevents context explosion

---

## File Structure

```
chatbot/prompts/
├── __init__.py
├── abbreviations.py                    # Existing
├── intent_classification_prompt.py     # Existing (keep for stateless)
├── reranking_prompt.py                 # Existing (keep for stateless)
├── response_generation_prompt.py       # Existing (keep for stateless)
├── location_search_prompt.py           # Existing
└── conversational/                     # NEW
    ├── __init__.py
    ├── reformulation_prompt.py
    ├── intent_classification_prompt.py
    ├── reranking_prompt.py
    ├── response_generation_prompt.py
    └── summarizer_prompt.py

evaluation/prompts/                     # NEW
├── __init__.py
└── multi_turn_judge_prompt.py
```

---

## Prompt Selection Logic

```python
# chatbot/prompts/conversational/__init__.py

def get_prompt(prompt_type: str, conversational: bool = False):
    """Get appropriate prompt variant based on conversation state."""
    if conversational:
        from . import conversational as conv
        return getattr(conv, f"{prompt_type}_prompt")
    else:
        from .. import prompts as stateless
        return getattr(stateless, f"{prompt_type}_prompt")
```

---

## Usage in Nodes

```python
# chatbot/graph/nodes/reformulate.py
from chatbot.prompts.conversational.reformulation_prompt import (
    REFORMULATION_SYSTEM, 
    REFORMULATION_USER
)

def reformulate_node(state: ConversationalRAGState) -> dict:
    messages = state.get("messages", [])
    
    if len(messages) <= 1:
        return {"reformulated_query": state["query"]}
    
    history = format_messages(messages[:-1])
    
    response = llm.invoke([
        SystemMessage(content=REFORMULATION_SYSTEM),
        HumanMessage(content=REFORMULATION_USER.format(
            history=history,
            query=state["query"]
        ))
    ])
    
    # Extract from XML tag
    reformulated = extract_tag(response.content, "reformulated_query")
    
    return {"reformulated_query": reformulated or state["query"]}
```

---

## Best Practices Applied

| Practice | Implementation |
|----------|----------------|
| **XML Tags** | All prompts use `<tag>` for structure and parsing |
| **Few-Shot Examples** | Reformulation includes examples, not rules |
| **Domain Context First** | System prompts lead with domain knowledge |
| **Compact Scoring Guides** | 1-line per score level, not paragraphs |
| **Graceful Fallbacks** | "If already standalone, return unchanged" |
| **Separation of Concerns** | Stateless vs conversational variants |
| **Token Awareness** | Summarizer has explicit token limit |
| **JSON in XML** | Judge uses JSON inside XML for structured output |

---

## References

- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering)
- [LangChain Prompt Templates](https://python.langchain.com/docs/modules/model_io/prompts/)
