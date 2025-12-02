# Conversational Intelligence Improvement Design

**Goal:** Improve RAG conversational intelligence from 62/100 to 80+ score
**Approach:** Enhanced prompts + improved heuristics (no architectural changes)

---

## Problem Summary

Current reformulation fails on 4 query types:

| Pattern | Example | Current Result | Root Cause |
|---------|---------|----------------|------------|
| **Topic Return** | "back to my application question" | "I couldn't find information" | No pattern detection |
| **Correction** | "Sorry, I meant family of 6" | Fails | No correction recognition |
| **Hypothetical** | "What if I get a raise to $45,000?" | "I don't have information" | Treated as retrieval query |
| **Negation** | "Which ones don't require employment?" | Wrong subject | Subject carryover lost |

---

## Solution: Two-Part Enhancement

### Part 1: Enhanced Heuristics

**File:** `chatbot/graph/nodes/reformulate.py`

Add new pattern groups to `needs_reformulation()` function (lines 72-101):

```python
# NEW: Correction patterns
correction_patterns = [
    r"\b(i meant|sorry|actually|no,?\s*i|correction)\b",
    r"\b(i said|i was asking|not \d+)\b",
]

# NEW: Topic return patterns
topic_return_patterns = [
    r"\b(back to|return to|going back|earlier|previous)\b",
    r"\b(my .* question|as i (asked|said)|originally)\b",
]

# NEW: Hypothetical/scenario patterns
hypothetical_patterns = [
    r"\b(what if|suppose|assuming|if i|if my)\b",
    r"\b(raise to|increase to|goes? up|changed? to)\b",
]

# NEW: Negation with carryover
negation_carryover_patterns = [
    r"^which (ones?|programs?) (don't|aren't)\b",
    r"^(the ones?|those) (that )?(don't|aren't)\b",
]
```

### Part 2: Enhanced Prompt

**File:** `chatbot/prompts/conversational/reformulation_prompt.py`

Replace minimal prompt with explicit instructions + few-shot examples:

**REFORMULATION_SYSTEM** - Add numbered instructions:
```
1. RESOLVE pronouns using conversation history
2. CORRECTIONS ("I meant X"): Replace prior parameter with new value
3. TOPIC RETURNS ("back to X"): Find referenced topic and reformulate as original question
4. HYPOTHETICALS ("what if X?"): Include user's stated context with new value
5. NEGATION CARRYOVER: Make subject from prior turn explicit
```

**REFORMULATION_USER** - Add critical few-shot examples:
```
Example - Correction:
Query: Sorry, I meant family of 6
Reformulated: What are the income limits for a family of 6?

Example - Topic return:
Query: Ok back to my application question
Reformulated: How do I apply for CCS?

Example - Hypothetical:
Query: What if I get a raise to $45,000?
Reformulated: Would a single parent with 2 children making $45,000/year qualify?

Example - Negation:
Query: Which ones don't require employment?
Reformulated: Which Texas childcare programs do NOT require employment?
```

---

## Files to Modify

| File | Change |
|------|--------|
| `chatbot/graph/nodes/reformulate.py` | Add 4 new pattern groups to `needs_reformulation()` |
| `chatbot/prompts/conversational/reformulation_prompt.py` | Replace both prompts with enhanced versions |

---

## Expected Impact

| Test | Current | Expected |
|------|---------|----------|
| Topic Switch & Return | 40 | 85 |
| Correction Handling | 45 | 90 |
| Hypothetical Application | 50 | 85 |
| Negation & Filtering | 55 | 80 |
| **Overall** | **62** | **85** |

---

## Verification

```bash
cd OAI_EXPERIMENT && python conversational_test_rag.py
```

Compare against baseline: `OAI_EXPERIMENT/test_results/conversational_test_rag.json`
