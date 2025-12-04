# Plan: Reduce RAG Response Verbosity

## Problem
RAG generations are too long and chatty compared to OpenAI agent responses.

## Comparison: OpenAI vs RAG Responses

### Example 1: "What percentage of SMI determines income eligibility?"

**OpenAI (1 sentence, 18 words):**
> 85 percent of the state median income (SMI) determines income eligibility for Low-Income child care under Texas CCS.

**RAG (4 sentences + bullet points, 94 words):**
> Income eligibility for Texas childcare assistance is limited to families whose income does **not exceed 85 % of the state's median income (SMI)**. This cap is applied both at initial eligibility determination and at every redetermination. The guideline is stated in the Child Care Services Guide and reiterated in the Child Care Workforce Strategic Plan.
> - **Child Care Services Guide**: "The child's family income does not exceed 85 percent of the SMI"...
> - **Child Care Workforce Strategic Plan**: "85 percent of the state's median income (SMI)"...

### Example 2: "Sorry, I meant family of 6"

**OpenAI (1 sentence):**
> For a family of 6, the income eligibility limit is: annual $121,495; monthly $10,125; weekly $2,336; bi-monthly $5,062; and bi-weekly $4,673.

**RAG (table + paragraph):**
> **2026 CCDF Income Limits – Family of 6**
> | Period | Income Limit |
> |--------|--------------|
> | Annual | **$121,495** |
> | Monthly | **$10,125** |
> ...
> These are the income eligibility thresholds for a six‑member household under the Texas Child Care Development Fund (CCDF) 2026 board contract year.

## Root Causes

1. **No brevity instruction in prompt** - Prompt says WHAT to include but not to be concise
2. **Markdown formatting encouragement** - RAG creates tables, headers, bullet points unnecessarily
3. **Over-citation** - RAG includes multiple citations and source explanations
4. **Explanatory padding** - RAG adds context sentences explaining what the data means

## Solution: Update Response Generation Prompt

**File:** `chatbot/prompts/response_generation_prompt.py`

Add these rules to both `RESPONSE_GENERATION_PROMPT` and `CONVERSATIONAL_RESPONSE_GENERATION_PROMPT`:

```
Response style:
- Be concise - answer in 1-3 sentences for simple questions
- Skip markdown formatting (tables, headers, bold) unless listing 4+ items
- One citation per fact is enough - don't repeat sources
- Don't explain what the data means if the user didn't ask
- For yes/no questions, start with Yes or No
```

## Implementation

### Step 1: Edit `chatbot/prompts/response_generation_prompt.py`

Add response style rules after "Key rules:" section in both prompts:

```python
RESPONSE_GENERATION_PROMPT = """You are an expert on Texas childcare assistance programs.

Answer the question using ONLY the provided documents. Always cite sources using [Doc X] format.

Key rules:
- Use the [Abbreviations] glossary for correct full names of organizations and programs
- State income limits with exact amounts and year/BCY
...existing rules...

Response style:
- Be concise - answer in 1-3 sentences for simple questions
- Skip markdown formatting (tables, headers, bold) unless listing 4+ items
- One citation per fact is enough - don't repeat sources
- Don't explain what the data means if the user didn't ask
- For yes/no questions, start with Yes or No

DOCUMENTS:
{context}
...
```

Apply same changes to `CONVERSATIONAL_RESPONSE_GENERATION_PROMPT`.

### Step 2: Test with conversational benchmarks

```bash
python tests/manual/conversational_benchmarks/run_rag.py
```

Compare output length to previous runs.

## Files to Modify

| File | Change |
|------|--------|
| `chatbot/prompts/response_generation_prompt.py` | Add response style rules |

## Expected Outcome

RAG responses should become similar in length/style to OpenAI:
- 1-3 sentences for factual questions
- Tables only for 4+ items
- Single citation per fact
- No explanatory padding
