# Generator History Injection for Multi-Hop Reasoning

**Date:** 2025-12-02
**Status:** Implemented
**Issue:** Multi-hop reasoning regression (95 → 75)
**Result:** Fixed - entity references now resolve correctly

---

## Problem

The conversational RAG system scored 85/100 overall, but Multi-Hop Reasoning regressed from 95 to 75. The root cause was that the generator lacked access to conversation history, causing failures when:

1. **Entity references** need resolution ("that family" → "family of 4")
2. **Synthesis** requires prior facts (85% SMI × $92,041 = $78,235)

### Failing Test Case

| Turn | Query | Result Before Fix |
|------|-------|-------------------|
| 1 | "What percentage of SMI determines eligibility?" | ✓ 85% |
| 2 | "What is SMI for family of 4?" | ✓ $92,041 |
| 3 | "Calculate the exact income cutoff for that family" | ❌ Wrong family size (returned family of 1) |
| 4 | "If family of 4 makes $4,500/month, qualify?" | ✓ Explicit values work |

**Root Cause:** The reformulator handles conversational anaphora (topic return, corrections) but NOT data-level entity references. The generator only received current query + retrieved chunks, not prior Q&A context.

---

## Solution

Inject last 3 Q&A pairs from conversation history into the generator prompt.

### Architecture Change

```
BEFORE:
REFORMULATE → CLASSIFY → RETRIEVE → RERANK → GENERATE
                                                  ↓
                                            chunks only

AFTER:
REFORMULATE → CLASSIFY → RETRIEVE → RERANK → GENERATE
                                                  ↓
                                        chunks + recent history
```

---

## Implementation

### 1. Config Setting

**File:** `chatbot/config.py`

```python
# Generator history injection for multi-hop reasoning
# Number of recent Q&A pairs to inject into generator prompt
GENERATOR_HISTORY_TURNS = 3
```

### 2. Conversational Response Prompt

**File:** `chatbot/prompts/response_generation_prompt.py`

Added new prompt template with `{history}` placeholder:

```python
CONVERSATIONAL_RESPONSE_PROMPT = """You are an expert on Texas childcare assistance programs.

<conversation_context>
{history}
</conversation_context>

Use the conversation context above to:
- Resolve entity references ("that family", "those programs", "the cutoff") to specific values
- Apply prior facts to calculations when requested
- Maintain consistency with previously stated information

Answer the question using ONLY the provided documents. Always cite sources using [Doc X] format.
...
"""
```

### 3. Generator Method Update

**File:** `chatbot/generator.py`

Updated `generate()` method to accept optional history:

```python
def generate(self, query: str, context_chunks: list, recent_history: str = None):
    context = self._format_context(context_chunks)

    if recent_history:
        prompt = CONVERSATIONAL_RESPONSE_PROMPT.format(
            history=recent_history,
            context=context,
            query=query
        )
    else:
        prompt = RESPONSE_GENERATION_PROMPT.format(context=context, query=query)
```

### 4. Generate Node History Extraction

**File:** `chatbot/graph/nodes/generate.py`

Added helper function and history extraction:

```python
def _format_recent_history(messages: list, max_turns: int) -> str:
    """Format last N Q&A pairs from conversation history."""
    if not messages or len(messages) < 2:
        return ""

    # Skip current query, extract completed Q&A pairs
    history_messages = messages[:-1]
    pairs = []
    i = 0
    while i < len(history_messages) - 1:
        if isinstance(history_messages[i], HumanMessage) and \
           isinstance(history_messages[i + 1], AIMessage):
            human_content = history_messages[i].content
            ai_content = history_messages[i + 1].content
            # Truncate long responses
            if len(ai_content) > 500:
                ai_content = ai_content[:500] + "..."
            pairs.append(f"Q: {human_content}\nA: {ai_content}")
            i += 2
        else:
            i += 1

    return "\n\n".join(pairs[-max_turns:])


def generate_node(state: dict) -> dict:
    # ... existing code ...

    # Extract recent history for conversational mode
    recent_history = None
    if "messages" in state and state["messages"]:
        recent_history = _format_recent_history(
            state["messages"],
            config.GENERATOR_HISTORY_TURNS
        )
        if recent_history:
            print(f"[Generate Node] Injecting {len(recent_history)} chars of history")

    # Pass history to generator
    result = generator.generate(query, reranked_chunks, recent_history=recent_history)
```

---

## Files Modified

| File | Change |
|------|--------|
| `chatbot/config.py` | Added `GENERATOR_HISTORY_TURNS = 3` |
| `chatbot/prompts/response_generation_prompt.py` | Added `CONVERSATIONAL_RESPONSE_PROMPT` |
| `chatbot/prompts/__init__.py` | Exported new prompt |
| `chatbot/generator.py` | Added `recent_history` param, conditional prompt |
| `chatbot/graph/nodes/generate.py` | Added `_format_recent_history()`, history injection |

---

## Results

### Test Verification

| Test | Turn 3 Query | Before | After |
|------|--------------|--------|-------|
| test_2b | "Calculate the exact income cutoff for that family" | ❌ Wrong: $47,862 (family of 1) | ✅ Correct: $78,235 (family of 4) |
| test_2 | "Based on what you told me, calculate..." | ❌ "I don't have enough information" | ✅ Calculates 85% × $92,041 |

### Log Output Confirmation

```
[Generate Node] Generating answer with openai/gpt-oss-20b
[Generate Node] Injecting 542 chars of conversation history
```

---

## Design Decisions

### Why 3 Turns?

- Sufficient for most multi-hop reasoning chains
- Keeps prompt size manageable (avoids token bloat)
- Balances context availability vs. latency/cost

### Why Truncate AI Responses to 500 chars?

- Prevents long responses from dominating the context window
- Key facts (numbers, entities) typically appear early in responses
- Full responses are still available via retrieval if needed

### Why Conditional Prompt?

- Only inject history when available (conversational mode)
- Stateless mode uses original prompt (no history overhead)
- Avoids confusing the generator with empty context blocks

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Longer prompts increase latency/cost | Limited to 3 turns, responses truncated to 500 chars |
| History may confuse unrelated queries | Prompt instructs generator to use only when relevant |
| Token limit exceeded | Oldest turns dropped first via slicing |

---

## Future Improvements

1. **Smart history selection** - Only inject history when entity references detected
2. **Entity extraction** - Pre-extract key entities (family sizes, amounts) for more targeted injection
3. **Configurable truncation** - Allow per-deployment tuning of response truncation length
