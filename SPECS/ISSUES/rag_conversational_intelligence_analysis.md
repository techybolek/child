# RAG Conversational Intelligence Analysis

**Date:** 2025-12-02
**System:** Custom RAG (LangGraph + Qdrant)
**Test Suite:** 7 conversational intelligence tests
**Version:** v3 (with `gpt-oss-120b` reformulator)

---

## Overall Scorecard

| Test | v1 Score | v2 Score | v3 Score | Change (v1→v3) |
|------|----------|----------|----------|----------------|
| Multi-Hop Reasoning | 95 | 75 | **75** | ⬇️ -20 |
| Topic Switch & Return | 40 | 95 | **95** | ⬆️ +55 |
| Negation & Filtering | 55 | 70 | **80** | ⬆️ +25 |
| Correction Handling | 45 | 80 | **85** | ⬆️ +40 |
| Comparative Reasoning | 60 | 50 | **85** | ⬆️ +25 |
| Hypothetical Application | 50 | 75 | **80** | ⬆️ +30 |
| Temporal Process | 90 | 90 | **95** | ⬆️ +5 |
| **Overall** | **62/100** | **76/100** | **85/100** | **⬆️ +23** |

### v3 Configuration
- **Reformulator:** `gpt-oss-120b` (upgraded from `gpt-oss-20b`)
- **Generator:** `gpt-oss-20b`
- **Reranker:** `gpt-oss-120b`

---

## Key Improvements (v1 → v3)

### Topic Switch & Return (40 → 95) ✅ FIXED
**Previous:** "Ok back to my application question" → "I couldn't find information"
**Current:** Reformulates to `"How do I apply for CCS?"` → Full CCS application steps

### Correction Handling (45 → 85) ✅ FIXED
**Previous:** "Sorry, I meant family of 6" → "I couldn't find information"
**Current:** Reformulates to `"What are the income limits for a family of 6?"` → Provides family of 6 limits

### Hypothetical Application (50 → 80) ✅ FIXED
**Previous:** "What if I get a raise to $45,000?" → "I don't have information on a raise"
**Current:** Reformulates to `"Would a single parent with 2 children making $45,000/year still qualify?"` → Yes, still eligible under 85% SMI

### Negation & Filtering (55 → 80) ✅ IMPROVED
**Previous:** "Which ones don't require employment?" → Listed excluded income sources (wrong subject)
**Current:** Reformulates to `"Which Texas childcare programs do NOT require employment to qualify?"` → Correctly identifies Initial Job Search program

### Comparative Reasoning (60 → 85) ✅ FIXED
**Previous:** "What if she's also a student?" → "I couldn't find information"
**Current:** Reformulates to `"What if the single mom working part-time is also a student?"` → Detailed education-based eligibility pathway

### Temporal Process (90 → 95) ✅ IMPROVED
Strong coreference resolution throughout 4-turn process sequence.

---

## Remaining Issue: Multi-Hop Reasoning (95 → 75) ⬇️ REGRESSED

### The Specific Failure: Test 2 & Test 2b, Turn 3

**Test 2b** was added to isolate whether the phrase "based on what you told me" caused the failure.

| Test | Turn 3 Query | Reformulated | Response | Result |
|------|--------------|--------------|----------|--------|
| **test_2** | "Based on what you told me, calculate the exact income cutoff for that family." | (unchanged) | "I don't have enough information... you would need to know the family's size" | ❌ Ignores prior context |
| **test_2b** | "Calculate the exact income cutoff for that family." | (unchanged) | "The annual income eligibility limit for a **one-member family** is $47,862" | ❌ Wrong family size! |

### Key Finding

**Both tests fail, but for different reasons:**

| Test | Failure Mode |
|------|--------------|
| test_2 | Claims insufficient information (ignores conversation history) |
| test_2b | Retrieves data but **wrong family size** - returns family of 1 instead of family of 4 |

### Root Cause Analysis

The issue is **NOT** the phrase "based on what you told me". Both phrasings fail.

**test_2b reveals the real problem:**
- The reformulator passed through "Calculate the exact income cutoff for that family" unchanged
- **"that family"** should resolve to **"family of 4"** from Turn 2
- Instead, retrieval grabbed data for family of 1 (first row in income table)

**The actual bug:** The reformulator doesn't resolve entity references like **"that family" → "family of 4"**

### What Should Happen

Turn 3 reformulation should be either:
> "Calculate the exact income cutoff for a family of 4 based on 85% of $92,041 SMI"

Or at minimum:
> "Calculate the exact income cutoff for a family of 4"

### Why Other Anaphoric References Work

| Pattern | Example | Works? |
|---------|---------|--------|
| Topic return | "back to my application question" → "How do I apply for CCS?" | ✅ |
| Corrections | "Sorry, I meant family of 6" → "income limits for family of 6" | ✅ |
| Pronouns with clear referent | "What if she's also a student?" → "What if the single mom..." | ✅ |
| **Entity reference to prior data** | "that family" → "family of 4" | ❌ |

The reformulator handles **conversational anaphora** but not **data-level entity references** from prior retrieved facts.

### Why Turn 4 Recovered

User rephrased with explicit numbers ("family of 4 makes $4,500 per month"), bypassing the need for coreference resolution.

---

## Detailed Test Results (v3)

### Test 2: Multi-Hop Reasoning - Score: 75/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "What percentage of SMI determines eligibility?" | (unchanged) | ✅ 85% |
| 2 | "What is the current SMI for family of 4?" | (unchanged) | ✅ $92,041/year |
| 3 | "Based on what you told me, calculate the cutoff" | (unchanged) | ❌ "I don't have enough information" |
| 4 | "If family of 4 makes $4,500/month, do they qualify?" | Reformulated | ✅ Yes, $4,500 < $7,670 |

**Issue:** Turn 3 synthesis request not handled - reformulator doesn't inject prior facts.

---

### Test 5: Topic Switch & Return - Score: 95/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "How do I apply for CCS?" | (unchanged) | ✅ Full 6-step process |
| 2 | "Wait, first tell me about Texas Rising Star" | (unchanged) | ✅ Complete TRS overview |
| 3 | "Ok back to my application question" | `"How do I apply for CCS?"` | ✅ Returns to CCS steps |

**Fixed:** Topic return now correctly resolves anaphoric reference.

---

### Test 3: Negation & Filtering - Score: 80/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "What programs require employment?" | (unchanged) | ✅ IJS, TANF, Low-Income |
| 2 | "Which ones don't require employment?" | `"Which TX programs do NOT require employment?"` | ✅ Initial Job Search |
| 3 | "Of those, which have highest income limits?" | `"Which TX programs without employment have highest limits?"` | ✅ CCDF $146,346 |

**Fixed:** Negation handling now maintains subject carryover.

---

### Test 4: Correction Handling - Score: 85/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "What are income limits for family of 4?" | (unchanged) | ✅ $92,041 annual |
| 2 | "Sorry, I meant family of 6" | `"What are income limits for family of 6?"` | ✅ Provides limits |
| 3 | "What documents do I need to prove that income?" | `"What documents...for family of 6...?"` | ✅ Income verification docs |

**Fixed:** Correction handling now maintains context for follow-up.

---

### Test 6: Comparative Reasoning - Score: 85/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "What's the difference between CCS and CCMS?" | (unchanged) | ✅ Program vs System |
| 2 | "Which one is better for a single mom part-time?" | (unchanged) | ✅ Subsidized childcare recommendation |
| 3 | "What if she's also a student?" | `"What if single mom part-time is also student?"` | ✅ Education-based eligibility |

**Fixed:** Student eligibility now correctly retrieved with education as qualifying activity.

---

### Test 7: Hypothetical Application - Score: 80/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "I'm a single parent with 2 kids, making $35,000/year" | (unchanged) | ✅ Eligible, PSoC $268/month |
| 2 | "Do I qualify for childcare assistance?" | (unchanged) | ⚠️ Generic guide (partial context loss) |
| 3 | "What if I get a raise to $45,000?" | `"Would single parent with 2 children making $45,000..."` | ✅ Still eligible |

**Partial:** Turn 3 scenario modification works, Turn 2 could better use prior context.

---

### Test 8: Temporal Process Reasoning - Score: 95/100

| Turn | Query | Reformulated | Result |
|------|-------|--------------|--------|
| 1 | "What happens after I submit my CCS application?" | (unchanged) | ✅ Full process sequence |
| 2 | "How long does that take?" | `"How long...verify CCS application?"` | ✅ 20 calendar days |
| 3 | "What if they need more documents?" | `"What if WDB needs additional documents?"` | ✅ Document request process |
| 4 | "And after that?" | `"What happens after additional documents?"` | ✅ Continues to eligibility decision |

**Excellent:** Temporal coreference resolution works consistently across 4 turns.

---

## Reformulation Quality Summary (v3)

| Pattern | v1 | v2 | v3 | Status |
|---------|-----|-----|-----|--------|
| Topic return ("back to X") | ❌ | ✅ | ✅ | Fixed |
| Corrections ("I meant X") | ❌ | ✅ | ✅ | Fixed |
| Scenario updates ("what if X") | ❌ | ✅ | ✅ | Fixed |
| Negation ("which don't") | ⚠️ | ⚠️ | ✅ | Fixed |
| Elliptical follow-ups ("What if she's also...") | ⚠️ | ❌ | ✅ | Fixed |
| **Entity references ("that family" → "family of 4")** | ❌ | ❌ | ❌ | **Still broken** |

---

## Single Remaining Issue

### Entity Reference Resolution Failure

**Pattern:** "that family", "those programs", "the cutoff" - references to data from prior turns

**Problem:** The reformulator doesn't resolve entity references that point to specific data values mentioned in prior assistant responses.

**Example (test_2b):**
- Turn 2: "What is SMI for **family of 4**?" → $92,041
- Turn 3: "Calculate the exact income cutoff for **that family**"
- Reformulated: (unchanged - "that family" not resolved)
- Result: Retrieves data for family of 1 instead of family of 4 ❌

**Why test_2 and test_2b both fail:**

| Test | Turn 3 | Failure Mode |
|------|--------|--------------|
| test_2 | "Based on what you told me, calculate..." | Generator claims insufficient info |
| test_2b | "Calculate the exact income cutoff for that family" | Wrong family size retrieved (1 instead of 4) |

**The phrase "based on what you told me" is not the cause** - test_2b proves the issue is unresolved "that family" reference.

**Why this is hard:**
- Reformulator handles conversational anaphora ("back to my question") but not data-level entity references
- "that family" requires parsing prior Q&A to extract "family of 4"
- Different from pronoun resolution - requires entity extraction from structured data in responses

---

## Potential Fixes

### Option 1: Entity Reference Resolution in Reformulator
Enhance reformulator to resolve data-level entity references:
- "that family" → extract family size from prior turns
- "those programs" → extract program names from prior turns
- "the cutoff" → extract specific values mentioned

**Implementation:** Parse prior assistant messages for key entities (family size, income amounts, program names) and inject into reformulated query.

### Option 2: Explicit Coreference Patterns
Add heuristic patterns to reformulator prompt:
- "that family" + prior mention of "family of N" → substitute "family of N"
- "that amount" + prior mention of "$X" → substitute "$X"
- "those programs" + prior list → substitute program names

### Option 3: Two-Pass Reformulation
1. First pass: Resolve conversational anaphora (pronouns, topic references)
2. Second pass: Resolve data-level entity references from conversation history

### Option 4: Generator Context Injection
Instead of fixing reformulator, inject prior Q&A pairs into generator prompt when calculation/synthesis keywords detected:
- "calculate", "compute", "what is the cutoff", "apply the percentage"

---

## Resolved Issues (v3)

| Issue | Status |
|-------|--------|
| Topic return failure | ✅ Fixed |
| Correction handling | ✅ Fixed |
| Negation subject carryover | ✅ Fixed |
| Elliptical context carryover | ✅ Fixed |
| Student eligibility gap | ✅ Fixed |
| Truncated reformulations | ✅ Fixed |

---

## Test Data Location

**Results:**
- Raw: `OAI_EXPERIMENT/test_results/conversational_test_rag.json`
- Human-readable: `OAI_EXPERIMENT/test_results/conversational_test_rag.txt`

**Test Definitions:**
- Conversational test YAML files in `QUESTIONS/conversations/`

---

## Comparison: RAG vs OpenAI Agent

| Metric | Custom RAG (v3) | OpenAI Agent (GPT-5) |
|--------|-----------------|----------------------|
| Overall Score | **85/100** | ~97/100 |
| Response Time | 4-7s avg | 15-25s avg |
| Cost | Low (GROQ) | High (GPT-5) |
| Transparency | High (sources shown) | Low (FileSearch black-box) |
| Conversational IQ | Good | Excellent |

**Gap reduced:** v3 narrowed the gap from 35 points to ~12 points. The remaining gap is primarily in **implicit synthesis** where GPT-5's reasoning mode excels at combining prior facts without explicit instruction.

---

## Version History

| Version | Date | Score | Key Changes |
|---------|------|-------|-------------|
| v1 | 2025-12-02 | 62/100 | Baseline with `gpt-oss-20b` reformulator |
| v2 | 2025-12-02 | 76/100 | Reformulation improvements |
| v3 | 2025-12-02 | **85/100** | Upgraded reformulator to `gpt-oss-120b` |
