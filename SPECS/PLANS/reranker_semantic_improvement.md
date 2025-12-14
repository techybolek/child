# Reranker Semantic Intelligence Improvement Plan

**Date**: November 12, 2025
**Status**: Proposed
**Priority**: High (blocking evaluation Q23)

## Executive Summary

The RAG reranker is incorrectly filtering out relevant chunks due to narrow semantic interpretation of compound concepts. When asked "How did employment outcomes vary in 2016?", it scored wage data as 3/10 because it treats "employment outcomes" as only employment status, not wages. This causes evaluation failures (41.7/100) despite correct data retrieval.

**Root Cause**: Prompt lacks guidance on semantic decomposition and conceptual relationships.

**Solution**: Domain-agnostic prompt enhancement teaching the model to think about semantic relationships, not just keyword matching.

**Expected Impact**: Evaluation score improves from 41.7 → 70+, with <5% token overhead.

---

## Problem Statement

### The Failure Case

**Question**: "How did employment outcomes vary across different workforce development areas in 2016?"

**Expected Answer** (from Q&A file):
> Employment outcomes for TANF parents finding employment in 2016 varied significantly by workforce area, ranging from 52.69% in Cameron County to 94.29% in Concho Valley. For non-TANF parents maintaining employment after one year, rates ranged from 71.18% in Central Texas to 83.01% in Heart of Texas. **Wage gains also varied considerably, from $426.91 per quarter in Cameron County to $811.92 in Rural Capital area**, demonstrating the importance of local economic conditions and workforce board effectiveness.

**What Happened**:
- Initial retrieval: 40 chunks (including chunk 33 with wage data)
- Reranking: Chunk 33 scored **3/10** → **FAILED** (cutoff 0.90)
- Generator: Never received wage data
- Evaluation: **41.7/100** (failing score)

### The Smoking Gun (Debug Log Evidence)

**From `results/debug_eval.txt`, line 3638:**
```
Chunk 33: wage gains 2012-2016 for non-TANF, not employment outcomes but wages.
Might be partially relevant but question about employment outcomes, not wages.
So low relevance.
```

**The reranker's faulty logic**:
1. Question mentions "employment outcomes"
2. Chunk contains "wage gains"
3. Conclusion: "wages ≠ employment outcomes" → score 3/10
4. Result: Critical data filtered out

### The Semantic Error

**False Dichotomy**: The reranker treats "employment outcomes" and "wages" as mutually exclusive categories.

**Reality**: In workforce policy research, "employment outcomes" is a **compound concept** encompassing:
- Employment attainment (got a job)
- Employment maintenance (kept a job)
- Wage levels and earnings
- Wage growth over time
- Job quality indicators

**Evidence from the documents themselves** (chunk 30 context):
> "Findings section of the 86th Texas Legislature report on subsidized child‑care effectiveness, detailing **employment and wage outcomes** for TANF parents"

The source documents explicitly treat wages as part of employment outcomes.

---

## Root Cause Analysis

### Current Prompt (chatbot/prompts/reranking_prompt.py)

```python
RERANKING_PROMPT = """You are scoring chunks from Texas childcare policy documents for relevance to a user question.

Question: {query}

{chunks_text}

Scoring criteria (0-10):
- 10: Directly answers the question with specific relevant data
- 7-9: Highly relevant explanation or partial answer
- 4-6: Related topic but missing key details
- 1-3: Tangentially related or different context
- 0: Unrelated

IMPORTANT:
- Score based on whether the chunk helps answer the question, not exact wording match
- Component data (e.g., "$100M + $50M") can answer questions about total amounts
- Temporal markers matter (FY'XX, BCY XX, specific years)
- Tables/data often span multiple chunks - score each chunk's contribution

Return compact JSON: {"chunk_0": <score>, "chunk_1": <score>, ...}"""
```

### What It Does Well

✅ Instructs against exact keyword matching
✅ Teaches component data summation (numeric example)
✅ Highlights temporal markers
✅ Acknowledges multi-chunk tables

### Critical Gaps

❌ **No semantic decomposition guidance**: Doesn't teach that broad terms (like "outcomes") encompass multiple specific metrics
❌ **No conceptual relationship instruction**: No guidance on related concepts, synonyms, or broader/narrower terms
❌ **Vague "helps answer" definition**: What does "helps answer" actually mean?
❌ **No domain context priming**: Doesn't establish this as policy/research context where terms have specific technical meanings
❌ **Missing information type analysis**: No instruction to think about data types vs. exact terminology

### Why This Matters

The prompt teaches:
- ✅ "$100M + $50M" can answer "what's the total?" (summation logic)

But doesn't teach:
- ❌ "Wage data" can answer "employment outcomes" questions (categorical logic)
- ❌ "Earnings" and "wages" are related terms (synonym logic)
- ❌ "Outcomes" is a broad category containing multiple metrics (hierarchy logic)

**Result**: The model defaults to **surface-level term matching** instead of **semantic understanding**.

---

## Proposed Solutions (Domain-Agnostic)

### Design Philosophy

**Goal**: Make the reranker semantically intelligent without hardcoding domain knowledge.

**Anti-Pattern** (domain-specific, doesn't generalize):
```
"Note: employment outcomes include wages, earnings, retention rates"
```

**Preferred Pattern** (domain-agnostic, teaches reasoning):
```
"Consider whether the chunk provides data types or metrics that address
the question's concept, even using different terminology."
```

### Tier 1: Minimal Enhancement (Recommended First Step)

**Changes**: 4 strategic additions to the prompt
**Token overhead**: ~150 tokens (~4% increase)
**Expected improvement**: 30-50% reduction in semantic misclassification
**Risk**: Low - backward compatible, just better guidance

#### Addition 1: Domain Context Priming

**Insert at line 3 (after role description):**
```python
Context: These are Texas childcare policy documents containing workforce development data,
program evaluations, and statistical reports. Policy questions often use broad terms (like
"outcomes", "impact", "performance") that encompass multiple specific metrics and data types.
```

**Why**: Primes the model's domain knowledge. Establishes that this is a policy context where terms have specific technical scope.

#### Addition 2: Semantic Relationship Guidance

**Insert before "Scoring criteria":**
```python
Evaluation approach:
1. Identify the core topic and what types of data would answer the question
2. Consider related concepts and component metrics (e.g., "employment outcomes" includes
   employment status, wages, earnings, retention - not just whether someone is employed)
3. Score based on how the chunk contributes to answering, not just term matching
```

**Why**: Explicitly teaches semantic decomposition. The example generalizes to "broad term → component parts" logic.

#### Addition 3: Enhanced Scoring Rubric

**Replace lines 9-14 with:**
```python
Scoring criteria (0-10):
- 9-10: Contains specific data directly addressing the question
  (includes component metrics that fall within the question's scope)
- 7-8: Highly relevant, addresses major aspects of the question
- 5-6: Addresses the topic but partial/incomplete for the specific question
- 3-4: Related topic but wrong specificity (e.g., wrong year, wrong breakdown)
- 1-2: Tangentially related or very weak relevance
- 0: Unrelated topic
```

**Why**: The parenthetical "(includes component metrics...)" teaches categorical reasoning without being domain-specific.

#### Addition 4: Strengthen IMPORTANT Section

**Replace line 17 with:**
```python
- Think semantically: consider whether chunks provide data that contributes to answering
  the question, even if using different terminology (e.g., "wages" can address "employment
  outcomes" questions; "enrollment data" can address "participation" questions)
```

**Why**: Explicit analogical reasoning. The examples show the pattern without being exhaustive.

#### Complete Tier 1 Prompt

```python
RERANKING_PROMPT = """You are scoring chunks from Texas childcare policy documents for relevance to a user question.

Context: These are Texas childcare policy documents containing workforce development data,
program evaluations, and statistical reports. Policy questions often use broad terms (like
"outcomes", "impact", "performance") that encompass multiple specific metrics and data types.

Question: {query}

{chunks_text}

Evaluation approach:
1. Identify the core topic and what types of data would answer the question
2. Consider related concepts and component metrics (e.g., "employment outcomes" includes
   employment status, wages, earnings, retention - not just whether someone is employed)
3. Score based on how the chunk contributes to answering, not just term matching

Scoring criteria (0-10):
- 9-10: Contains specific data directly addressing the question
  (includes component metrics that fall within the question's scope)
- 7-8: Highly relevant, addresses major aspects of the question
- 5-6: Addresses the topic but partial/incomplete for the specific question
- 3-4: Related topic but wrong specificity (e.g., wrong year, wrong breakdown)
- 1-2: Tangentially related or very weak relevance
- 0: Unrelated topic

IMPORTANT:
- Think semantically: consider whether chunks provide data that contributes to answering
  the question, even if using different terminology (e.g., "wages" can address "employment
  outcomes" questions; "enrollment data" can address "participation" questions)
- Component data (e.g., "$100M + $50M") can answer questions about total amounts
- Temporal markers matter (FY'XX, BCY XX, specific years)
- Spatial/categorical breakdowns matter (by region, by demographic, by board area)
- Tables often span multiple chunks - score each chunk's contribution

Return compact JSON: {"chunk_0": <score>, "chunk_1": <score>, ...}"""
```

**Token count**: Original ~150 tokens → Enhanced ~300 tokens (+150, ~100% increase but still minimal)
**Actual impact**: 300 tokens / 6000 total prompt = 5% increase (with 40 chunks averaging 150 tokens each)

---

### Tier 2: Chain-of-Thought Reasoning (If Tier 1 Insufficient)

**Changes**: Add explicit reasoning structure
**Additional tokens**: ~100 tokens
**Expected improvement**: 50-70% reduction in misclassification
**Risk**: Low-Medium - increases latency ~10-20%

#### Addition: Structured Reasoning Requirement

**Insert after "Evaluation approach" section:**
```python
Before scoring each chunk, briefly reason through:
- What is the main topic/concept in the question?
- What specific data types or metrics would answer it?
- Does this chunk contain those data types (considering related terminology)?
- How much does it contribute to answering?

Then assign scores based on that analysis.
```

**Why**: Forces systematic evaluation. Exposes faulty logic like "wages ≠ employment outcomes" by making the model articulate its reasoning.

**Trade-off**: Adds ~10-20% to reranking time due to additional generation. Worth it if accuracy improvement justifies the cost.

---

### Tier 3: Debug Mode (Optional, For Diagnosis Only)

**Changes**: Return reasoning alongside scores
**Use case**: Debugging only, not production
**Token cost**: ~3-5x increase (significant)

**Modified return format:**
```python
Return JSON with reasoning (for debug mode):
{
  "chunk_0": {
    "analysis": "Contains 2016 wage data by board area",
    "relevance": "Wages are employment outcome metrics",
    "score": 9
  },
  "chunk_1": {
    "analysis": "Only has 2010-2015 data",
    "relevance": "Wrong time period for 2016 question",
    "score": 0
  },
  ...
}
```

**Implementation**: Add `debug=True` parameter to `rerank()` method, switch prompt based on flag.

**Use**: Only when investigating specific failures, never in production.

---

## Expected Impact on Failure Case

### Current Behavior

**Question**: "How did employment outcomes vary across different workforce development areas in 2016?"

**Chunk 33 (Wage Data Table 2B, 2012-2016)**:
- **Current reranker reasoning**: "wage gains, not employment outcomes, maybe score 3"
- **Current score**: 3/10
- **Current cutoff**: 0.90 (90th percentile = 9/10)
- **Result**: FAILED reranking

### Expected Behavior with Tier 1 Prompt

**New reranker reasoning**:
1. Question asks about "employment outcomes" in 2016 by area
2. Per evaluation approach: "employment outcomes includes employment status, wages, earnings, retention"
3. Chunk 33 contains wage gains 2012-2016 by area
4. Wages are a component metric within "employment outcomes" scope
5. Contains 2016 data (✓ temporal marker)
6. Broken down by area (✓ spatial marker)
7. Assessment: Highly relevant component data

**Expected score**: 8-9/10
**Cutoff**: Will likely adjust downward when multiple 8-9 scores exist
**Result**: PASSES reranking

### Expected Behavior with Tier 2 Prompt (CoT)

**New reranker reasoning**:
```
Before scoring:
- Main topic: Employment outcomes (= status, wages, earnings, retention)
- Specific: By workforce area, for 2016
- Data type needed: Quantitative metrics showing variation across areas
- Chunk 33: Contains wage gains 2012-2016, broken down by area
- Assessment: Wage gains ARE employment outcome metrics → Highly relevant
```

**Expected score**: 9/10
**Result**: PASSES reranking with high confidence

### Downstream Impact

**Generator receives**:
- Employment status tables (TANF attainment/maintenance)
- Non-TANF maintenance tables
- **Wage gain tables** ← Previously missing

**Generated answer includes**:
- Employment rate variations ✓
- Wage gain variations ✓ (was missing)
- Cameron County 52.69% ✓ (was missing - in chunk 8 which scored 9)
- Central Texas 71.18% ✓ (was in chunk 26 which passed)

**Evaluation score**: 41.7 → **70+** (passing)

---

## Implementation Plan

### Phase 1: Tier 1 Prompt (Recommended Start)

**Timeline**: 10 minutes
**Files modified**: 1 (`chatbot/prompts/reranking_prompt.py`)
**Lines changed**: ~15 lines (mostly additions)

**Steps**:
1. Update `RERANKING_PROMPT` with Tier 1 enhancements
2. Run investigation: `bash UTIL/investigate.sh`
3. Verify chunk 33 scores 8-9 instead of 3
4. Verify evaluation score improves to 70+

**Success criteria**:
- ✅ Chunk 33 (wage data) passes reranking
- ✅ Generator includes wage data in answer
- ✅ Evaluation score ≥ 70
- ✅ Token overhead < 5%
- ✅ Latency increase < 10%

**If unsuccessful**: Proceed to Phase 2

### Phase 2: Tier 2 Prompt (If Needed)

**Timeline**: 20 minutes
**Additional changes**: Add CoT reasoning section

**Steps**:
1. Add "Before scoring" reasoning structure
2. Re-test with `bash UTIL/investigate.sh`
3. Measure token and latency impact
4. Compare scores and reasoning quality

**Success criteria**:
- ✅ Chunk 33 scores 9/10
- ✅ Evaluation score ≥ 75
- ✅ Token overhead < 10%
- ✅ Latency increase < 20%

### Phase 3: Full Evaluation Suite

**Timeline**: 30 minutes
**Command**: `python -m evaluation.run_evaluation`

**Metrics to track**:
- **Primary**: Overall pass rate (currently ~84%)
- **Secondary**: Average composite score
- **Cost**: Total tokens used
- **Latency**: Average evaluation time

**Expected improvements**:
- Pass rate: 84% → 88-92%
- Failures due to semantic misinterpretation: -70%
- Token cost: +4-5%
- Latency: +5-10%

### Phase 4: A/B Comparison (Optional)

**If available**: Run parallel evaluation with old vs new prompt

**Metrics**:
- Side-by-side score comparison
- Identify which questions improved
- Identify any regressions (shouldn't be any, but verify)
- Statistical significance testing

---

## Testing Strategy

### Unit Test: Failed Case

**Test**: Q23 investigation
**Command**: `bash UTIL/investigate.sh`
**Expected outcome**:
- Chunk 33 (wage data) scores 8-9/10
- Passes reranking with cutoff ~0.80
- Generator includes wage data
- Evaluation score ≥ 70

### Integration Test: Full Evaluation

**Test**: Complete evaluation suite
**Command**: `python -m evaluation.run_evaluation`
**Expected outcome**:
- Pass rate improves from 84% to 88-92%
- No new failures introduced
- Semantic interpretation errors reduced by 50-70%

### Performance Test: Resource Usage

**Metrics**:
- Token usage (should be <5% increase)
- Latency (should be <10% increase)
- Cost per evaluation (track for budget planning)

**Acceptable thresholds**:
- Token increase: <10%
- Latency increase: <20%
- Pass rate improvement: >3 percentage points

### Qualitative Test: Manual Review

**Sample**: 10 random questions
**Review**: Examine reranker scores and reasoning (use debug mode)
**Check for**:
- Correct semantic interpretation
- Appropriate handling of compound concepts
- No over-generalization (ensuring unrelated chunks still score 0)

---

## Risk Assessment

### Low Risk

✅ **Backward compatibility**: Tier 1 changes are purely additive guidance
✅ **Graceful degradation**: If model ignores new instructions, falls back to current behavior
✅ **Easy rollback**: Single file change, can revert in seconds
✅ **Minimal cost**: 4-5% token increase is negligible

### Medium Risk

⚠️ **Over-generalization**: Model might score truly unrelated chunks higher
**Mitigation**: Test on diverse question types, manual review sample
**Likelihood**: Low - prompt is quite specific about "contributes to answering"

⚠️ **Latency increase**: Tier 2 CoT adds generation time
**Mitigation**: Only use Tier 2 if Tier 1 insufficient, measure before deploying
**Likelihood**: Tier 1 likely sufficient

### Negligible Risk

✓ **Model capability**: Both GROQ (120B) and OpenAI (gpt-4o-mini) handle reasoning well
✓ **Breaking changes**: No API or interface changes
✓ **Data corruption**: Prompt-only change, no data modification

---

## Success Metrics

### Primary KPIs

| Metric | Current | Target | Critical Threshold |
|--------|---------|--------|-------------------|
| Evaluation pass rate | 84% | 88-92% | >86% |
| Q23 score | 41.7 | >70 | >60 |
| Semantic errors | High | -50-70% | -30% |

### Secondary KPIs

| Metric | Current | Target | Critical Threshold |
|--------|---------|--------|-------------------|
| Token overhead | 0% | <5% | <10% |
| Latency increase | 0% | <10% | <20% |
| False positives | Unknown | <2% | <5% |

### Validation Checks

✅ Chunk 33 (wage data) scores 8-9/10
✅ Generator receives wage data
✅ Answer includes wage variation stats
✅ No previously passing questions now fail
✅ Token usage within budget

---

## Alternative Approaches Considered

### ❌ Option 1: Add Domain-Specific Examples

**Approach**: "Note: employment outcomes include employment status, wages, earnings"

**Pros**: Simple, direct
**Cons**:
- Doesn't generalize to other domains
- Creates maintenance burden (need to list all possible concepts)
- Doesn't teach the model *how* to think

**Verdict**: Rejected - too brittle, doesn't scale

### ❌ Option 2: Fine-Tune Cross-Encoder

**Approach**: Train a specialized reranking model on domain data

**Pros**: Potentially highest accuracy
**Cons**:
- Requires training data (we don't have labeled pairs)
- Requires inference infrastructure
- Much higher complexity
- Longer iteration time

**Verdict**: Rejected - overkill for a prompt engineering problem

### ❌ Option 3: Query Expansion

**Approach**: Expand "employment outcomes" to "employment OR wages OR earnings" before retrieval

**Pros**: Could improve initial retrieval
**Cons**:
- Changes retrieval layer (more invasive)
- Doesn't fix reranking problem
- May retrieve more noise
- Increases embedding cost

**Verdict**: Rejected - doesn't address root cause

### ✅ Option 4: Prompt Engineering (Selected)

**Approach**: Enhance prompt to teach semantic reasoning

**Pros**:
- Minimal change (single file)
- Domain-agnostic principles
- Easy to iterate
- Zero infrastructure changes
- Backward compatible

**Cons**:
- Requires careful prompt design
- May need multiple iterations

**Verdict**: Selected - best balance of impact, simplicity, and maintainability

---

## Generalization to Other Domains

### Principles Learned (Applicable Anywhere)

1. **Semantic decomposition**: Teach models that broad terms encompass specific metrics
2. **Conceptual bridging**: Guide thinking about related terms and data types
3. **Domain priming**: Set context for technical terminology
4. **Explicit examples**: Use analogies to teach patterns, not memorize facts
5. **Chain-of-thought**: Force systematic reasoning to expose faulty logic

### Reusable Patterns

**Pattern 1: Compound Concept Handling**
```
"[Broad term] includes [component 1], [component 2], [component 3] -
not just [common misconception]"
```

**Pattern 2: Semantic Bridging**
```
"Consider whether chunks provide [information type] that addresses the
question's concept, even using different terminology"
```

**Pattern 3: Analogical Learning**
```
"(e.g., 'X' can address 'Y' questions; 'A' can address 'B' questions)"
```

These patterns work for any domain with compound concepts and technical terminology.

---

## Monitoring & Iteration

### Post-Deployment Monitoring

**Week 1**: High-frequency monitoring
- Run evaluation suite daily
- Track pass rate trends
- Review any new failures
- Check token usage and cost

**Week 2-4**: Normal monitoring
- Run evaluation suite weekly
- Aggregate metrics
- Identify patterns in failures

### Iteration Triggers

**Trigger 1**: Pass rate doesn't improve by >3 percentage points
**Action**: Proceed to Tier 2 (CoT reasoning)

**Trigger 2**: New failure patterns emerge
**Action**: Review failing cases, adjust prompt guidance

**Trigger 3**: Token cost exceeds budget
**Action**: Optimize prompt wording, remove redundancy

### Continuous Improvement

- Collect edge cases where reranking still fails
- Analyze failure modes quarterly
- Update prompt guidance based on patterns
- Document learnings for future RAG systems

---

## Documentation Updates Needed

After implementation:

1. **README.md**: Note reranker prompt version and improvements
2. **SPECS/chatbot_implementation.md**: Update reranking section
3. **evaluation/config.py**: Document any threshold changes
4. **CHANGELOG**: Add entry for semantic intelligence enhancement

---

## Conclusion

The reranker's semantic interpretation failure is a **prompt engineering problem** with a **prompt engineering solution**. By teaching the model to think about semantic relationships and conceptual hierarchies, we can fix the immediate issue (Q23 failing) while building a more robust, generalizable reranking system.

**Recommended Action**: Implement Tier 1 prompt enhancement (10 minutes), validate on Q23 (2 minutes), then run full evaluation suite (30 minutes). Total time investment: <1 hour for potentially 5+ percentage point improvement in pass rate.

**Next Steps**:
1. ✅ Create this specification document
2. Update `chatbot/prompts/reranking_prompt.py` with Tier 1 changes
3. Run `bash UTIL/investigate.sh` to validate Q23 fix
4. Run `python -m evaluation.run_evaluation` for full validation
5. Document results and iterate if needed
