# Plan: Generator History Injection for Multi-Hop Reasoning

**Date:** 2025-12-02
**Issue:** Multi-hop reasoning regression (95 → 75)
**Target:** Restore to 95+ score

---

## Problem Summary

The generator lacks access to conversation history, causing failures when:
1. Entity references need resolution ("that family" → "family of 4")
2. Synthesis requires prior facts (85% SMI × $92,041 = $78,235)

### Failing Test Case (test_2/test_2b)

| Turn | Query | Issue |
|------|-------|-------|
| 1 | "What percentage of SMI determines eligibility?" | ✓ Returns 85% |
| 2 | "What is SMI for family of 4?" | ✓ Returns $92,041 |
| 3 | "Calculate the exact income cutoff for that family" | ✗ "that family" unresolved, no prior facts |
| 4 | "If family of 4 makes $4,500/month, do they qualify?" | ✓ Explicit values work |

---

## Solution: Inject Recent History into Generator

### Approach

For conversational mode, pass last 2-3 Q&A pairs to generator prompt alongside retrieved chunks.

### Current Flow
```
REFORMULATE → CLASSIFY → RETRIEVE → RERANK → GENERATE
                                                  ↓
                                            chunks only
```

### New Flow
```
REFORMULATE → CLASSIFY → RETRIEVE → RERANK → GENERATE
                                                  ↓
                                        chunks + recent history
```

---

## Implementation

### File: `chatbot/graph/nodes/generate.py`

1. Check if conversational mode is enabled
2. Extract last N turns from `state["messages"]`
3. Format as `<conversation_context>` block
4. Prepend to generator prompt before chunks

### File: `chatbot/prompts/response_generation_prompt.py`

Add instruction to use conversation context:

```
<conversation_context>
{recent_history}
</conversation_context>

Use the conversation context above to:
- Resolve entity references ("that family", "those programs")
- Apply prior facts to calculations when requested
- Maintain consistency with previously stated information
```

### Config: `chatbot/config.py`

Add:
```python
GENERATOR_HISTORY_TURNS = 3  # Number of recent Q&A pairs to inject
```

---

## Tests

### Test File: `OAI_EXPERIMENT/test_generator_history.py`

#### Test 1: Entity Reference Resolution
```yaml
conversation:
  - turn: 1
    user: "What is the SMI for a family of 4?"
    expected: "$92,041"
  - turn: 2
    user: "What is the income cutoff for that family?"
    expected_contains: ["family of 4", "$78,235"]  # 85% of $92,041
    requires_context: true
```

#### Test 2: Multi-Hop Calculation
```yaml
conversation:
  - turn: 1
    user: "What percentage of SMI determines eligibility?"
    expected: "85%"
  - turn: 2
    user: "What is the SMI for family of 4?"
    expected: "$92,041"
  - turn: 3
    user: "Calculate the exact income cutoff for that family"
    expected_contains: ["$78,235", "85%", "$92,041"]
    requires_context: true
    requires_synthesis: true
```

#### Test 3: History + New Retrieval Combined
```yaml
conversation:
  - turn: 1
    user: "What are the income limits for a family of 4?"
    expected: "$92,041"
  - turn: 2
    user: "What about activity requirements?"
    expected_contains: ["25 hours", "single parent"]
  - turn: 3
    user: "I make $80,000 and work 30 hours. Do I qualify?"
    expected_contains: ["eligible", "qualify"]
    requires_context: true  # Needs family size from turn 1
    requires_retrieval: true  # May need additional criteria
```

#### Test 4: Entity Reference with Correction
```yaml
conversation:
  - turn: 1
    user: "What is the SMI for a family of 4?"
    expected: "$92,041"
  - turn: 2
    user: "Sorry, I meant family of 6"
    expected_contains: ["family of 6"]
  - turn: 3
    user: "What is the cutoff for that family?"
    expected_contains: ["family of 6"]  # Should resolve to corrected value
    requires_context: true
```

#### Test 5: Pronoun Chain Resolution
```yaml
conversation:
  - turn: 1
    user: "Tell me about the TANF program"
    expected_contains: ["TANF"]
  - turn: 2
    user: "What are the income limits for it?"
    expected_contains: ["TANF", "income"]
  - turn: 3
    user: "Are those limits the same for all family sizes?"
    expected_contains: ["family size", "limits"]
    requires_context: true  # "those limits" = TANF limits
```

---

## Validation

### Run Tests
```bash
cd OAI_EXPERIMENT && python test_generator_history.py
```

### Run Full Conversational Suite
```bash
cd OAI_EXPERIMENT && python conversational_test_rag.py
```

### Expected Results

| Test | Current | Target |
|------|---------|--------|
| Multi-Hop Reasoning | 75 | 95 |
| Overall Score | 85 | 90+ |

---

## Files to Modify

| File | Change |
|------|--------|
| `chatbot/graph/nodes/generate.py` | Extract and inject recent history |
| `chatbot/prompts/response_generation_prompt.py` | Add conversation context instructions |
| `chatbot/config.py` | Add `GENERATOR_HISTORY_TURNS` setting |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Longer prompts increase latency/cost | Limit to 3 turns, summarize if needed |
| History may confuse unrelated queries | Generator prompt instructs to ignore if not relevant |
| Token limit exceeded | Truncate oldest turns first |

---

## Success Criteria

1. Test 2 (Multi-Hop Reasoning) passes at 95+
2. Test 2b (Direct calculation) passes
3. No regression on other conversational tests
4. Overall score ≥ 90/100
