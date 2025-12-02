# Dense vs OpenAI Evaluation Analysis

**Date:** 2025-12-01
**Runs:** `results/dense/RUN_20251201_164944` vs `results/openai/RUN_20251201_164944`
**Questions:** 392

## Summary

| Metric | Dense | OpenAI |
|--------|-------|--------|
| Composite Score | 62.7 | 64.3 |
| Pass Rate | 52.6% | 51.3% |
| Avg Response Time | 4.19s | 10.26s |

Performance is similar overall. Dense is 2.5x faster.

## Key Patterns

### Dense Excels At
| Category | Dense | OpenAI | Diff |
|----------|-------|--------|------|
| table_reference | 96.5 | 50.0 | +46.5 |
| when (temporal) | 77.9 | 53.5 | +24.4 |
| short_question | 91.5 | 74.4 | +17.1 |

### OpenAI Excels At
| Category | Dense | OpenAI | Diff |
|----------|-------|--------|------|
| eligibility | 72.8 | 88.9 | -16.1 |
| requirements | 50.7 | 60.6 | -9.8 |
| enumeration | 62.0 | 71.0 | -9.0 |

## Critical Finding: Income Eligibility Tables

**Biggest gap:** `bcy-26-income-eligibility-and-maximum-psoc-twc.pdf` — OpenAI +28.9 points

### Root Cause

The PDF contains two structurally identical tables:
1. Income Eligibility Limits (family sizes 1-15)
2. Maximum Parent Share of Cost (family sizes 1-15)

Docling extracted them as 3 chunks:
- Chunk 0: Income table (no label)
- Chunk 1: PSOC table (no label)
- Chunk 2: Header text

**Problem:** Both tables have identical columns (Family Size, Annual, Monthly, Weekly, Bi-Monthly, Bi-Weekly) with no distinguishing labels. The LLM cannot tell which table is which and frequently swaps values.

### Example Failures

**Q9:** "Family of 12 bi-monthly income eligibility and PSOC?"
- Dense answered: Income=$403, PSOC=$5,753 (REVERSED)
- Correct: Income=$5,753, PSOC=$403

**Q3:** "What happens to income limits beyond 6 members?"
- Dense quoted PSOC values ($8,698, $8,891...) instead of income limits ($124,256, $127,017...)

**Q7:** "Weekly income limit for family of 4?"
- Dense said $124 (that's PSOC weekly)
- Correct: $1,770 (income eligibility weekly)

## Recommended Fix

Add table titles to chunks during extraction/loading:

```markdown
## Income Eligibility Limits
| Family Size | Annual | Monthly | ...

## Maximum Parent Share of Cost
| Family Size | Annual | Monthly | ...
```

This would disambiguate the tables for semantic search and LLM comprehension.

## Files Where Dense Wins (+5 to +8)
- tx3c-desk-aid-prospective-payment (+7.9)
- early-childhood-system-needs-assessment (+7.2)
- bcy-26-psoc-chart (+6.7)

## Files Where OpenAI Wins (-10 to -29)
- bcy-26-income-eligibility (-28.9)
- provider-attendance-matrix (-24.0)
- stakeholder-input-trs (-18.6)
- bcy26-board-max-provider-payment-rates (-12.8)

## Conclusion

Dense performs well on narrative content and context-heavy questions. OpenAI's FileSearch better preserves table structure and labels. The primary improvement opportunity is fixing table extraction to include distinguishing headers.
