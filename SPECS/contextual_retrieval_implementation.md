# Contextual Retrieval Implementation Plan

## Executive Summary
Implement three-tier hierarchical context generation to improve RAG retrieval accuracy. The failing test case (income eligibility question) demonstrates correct chunk exists but ranks 24th (outside top-20 retrieval limit). Adding rich contextual metadata will improve semantic similarity scoring and push the correct chunk into the retrieval window.

**Approach**: Three-tier context hierarchy using GROQ's existing RAG model (`openai/gpt-oss-20b`)
- **Tier 1**: Master context (static, all documents)
- **Tier 2**: Document-level context (generated once per PDF by analyzing first 2000 chars)
- **Tier 3**: Chunk-level context (generated per chunk using document context)

---

## Implementation Strategy

### Architecture: Three-Tier Context Cascade

```
PROMPTING FLOW:
Master Context (static)
    ↓
[Used to inform Document Context generation]
    ↓
Document Context (generated per PDF)
    ↓
[Used to inform Chunk Context generation]
    ↓
Chunk Context (generated per chunk)
    ↓
[Prepended to chunk content before embedding]
    ↓
Final Chunk = [Master + Document + Chunk Context] + Original Content
```

### Tier 1: Master Context (Static)

**Content** (Fixed, reused for all 37 PDFs):
```
This is official Texas Workforce Commission (TWC) documentation regarding childcare assistance programs. The content covers program eligibility requirements, income limits, payment procedures, provider regulations, and administrative guidelines for childcare services in Texas. The primary programs discussed are the Child Care Development Fund (CCDF) and Provider Services Operational Consultation (PSOC).
```

**Characteristics**:
- ~50 tokens
- Domain-establishing (Texas, TWC, childcare)
- Program identifiers (CCDF, PSOC)
- Scope statement (eligibility, income, payment, procedures)
- Pre-loaded at pipeline start

---

### Tier 2: Document-Level Context

**When Generated**: Once per PDF, during `process_pdf()`
**Input**: First 2000 characters of PDF content
**Cache**: `LOAD_DB/checkpoints/doc_context_{pdf_id}.json`

**Prompt Template**:
```
MASTER CONTEXT:
{master_context}

---

You are analyzing a Texas Workforce Commission document. Given the master context above, analyze this document excerpt and provide a focused 100-150 token summary.

DOCUMENT METADATA:
- Filename: {document_title}
- Source: {source_url}
- Total Pages: {total_pages}

DOCUMENT EXCERPT (first ~2000 chars):
{first_2000_chars}

---

Provide a summary that includes:
1. **Document Purpose**: What specific aspect of Texas childcare assistance does this document address? (e.g., income eligibility limits, provider payment procedures, application requirements, etc.)
2. **Key Programs/Policies**: Which childcare programs are covered? (CCDF, PSOC, TWC assistance, etc.)
3. **Target Audience**: Who is this document for? (families, providers, case managers, administrators)
4. **Key Metrics/Thresholds**: Any specific dollar amounts, percentages, family sizes, or income limits mentioned?
5. **Document Type**: Is this a policy guide, desk aid, form, FAQ, procedure manual, etc.?

Summary:"""
```

**Why This Design**:
- Includes master context to keep document context aligned with domain
- Asks for specific metrics/thresholds (critical for income eligibility questions)
- Distinguishes between CCDF, PSOC, etc. (crucial for the failing test which asks about maximum income)
- Helps identify target audience and document type

**Example Output** (for BCY 2026 income eligibility PDF):
> "This TWC desk aid specifies Board Contract Year (BCY) 2026 income eligibility limits for CCDF childcare assistance in Texas. It presents maximum family income thresholds by family size and pay period frequency (weekly, bi-weekly, monthly, annual), replacing the previous 85% State Median Income (SMI) standard. Intended for program administrators and case managers processing CCDF eligibility determinations. Key metrics: Family of 5 maximum bi-weekly income is $4,106, with annual limit of $106,768."

---

### Tier 3: Chunk-Level Context

**When Generated**: During `upload_documents_to_qdrant()`, in batches of 10
**Input**: Chunk text (up to 1000 chars after splitting), document context from Tier 2
**Processing**: Per-PDF sequential (generate doc context → all chunk contexts for that PDF → next PDF)

**Prompt Template**:
```
DOCUMENT CONTEXT:
{document_context}

---

You are processing a chunk from this document. Generate a precise 50-100 token context that helps retrieve this specific chunk when answering childcare assistance questions.

CHUNK METADATA:
- Page {page_num} of {total_pages}
- Chunk {chunk_index} of {total_chunks}

CHUNK CONTENT (first ~500 chars):
{chunk_text[:500]}

---

Generate a context that:
1. **Topic ID**: What is the main topic? (e.g., "Income eligibility limits for CCDF", "Monthly payment procedures", "Documentation requirements")
2. **Specificity**: What programs, family sizes, amounts, or percentages are mentioned?
3. **Distinction**: What makes this chunk unique from others in the document?
4. **Query Match**: What search terms or questions would this chunk answer?

Context:"""
```

**Why This Design**:
- Uses document context from Tier 2 to maintain consistency
- Emphasizes specificity (programs, amounts, family sizes)
- Asks for "query match" to bridge between chunk content and likely user questions
- Focused on retrieval relevance (what questions would retrieve this chunk?)

**Example Output** (for the failing test's correct chunk):
> "This section from the BCY 2026 income limits document provides maximum monthly and bi-weekly income thresholds for CCDF families of various sizes (1-7+ members). The specific values for a family of 5 earning bi-weekly are $4,106 maximum per pay period. This chunk distinguishes between pay period types (weekly/bi-weekly/monthly/annual) and supersedes the older 85% SMI standards used in 2025-2027 guidance documents."

---

### Final Chunk Assembly

Each chunk in Qdrant will contain:

```
[MASTER CONTEXT]
This is official Texas Workforce Commission (TWC) documentation...

[DOCUMENT CONTEXT]
This TWC desk aid specifies Board Contract Year (BCY) 2026 income...

[CHUNK CONTEXT]
This section from the BCY 2026 income limits document provides...

[ORIGINAL CHUNK CONTENT]
Family of 5
Maximum income per pay period: $4,106
Maximum annual income: $106,768
...
```

---

## Prompt Organization

All prompts are stored in a dedicated directory: `LOAD_DB/prompts/` with separate files for each prompt type.

**Directory Structure:**
```
LOAD_DB/
├── prompts/
│   ├── __init__.py
│   ├── master_context_prompt.py      # Static master context string
│   ├── document_context_prompt.py    # Document-level context generation prompt
│   └── chunk_context_prompt.py       # Chunk-level context generation prompt
├── contextual_processor.py           # Imports prompts from prompts/ directory
└── ...
```

Each prompt file exports a function/constant:
- `master_context_prompt.py`: `MASTER_CONTEXT` (string constant)
- `document_context_prompt.py`: `build_document_context_prompt(master_context, document_title, source_url, total_pages, first_2000_chars)` → returns formatted prompt string
- `chunk_context_prompt.py`: `build_chunk_context_prompt(document_context, page_num, total_pages, chunk_index, total_chunks, chunk_text)` → returns formatted prompt string

---

## Qdrant Collection Strategy: Head-to-Head Comparison

To enable side-by-side comparison of old vs. new retrieval quality:

**Original Collection**: `tro-child-1` (existing, no contextual chunks)
**Contextual Collection**: `tro-child-1-contextual` (new, with three-tier context)

**Configuration**:
```python
# LOAD_DB/config.py
QDRANT_COLLECTION_NAME = 'tro-child-1'                    # Original (unchanged)
QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1-contextual'  # New with context
```

**Comparison Workflow**:
```bash
# Before implementation
python test_failed.py  # Uses tro-child-1 (old)
# Output: Wrong answer ($3,918 from 85% SMI)

# After implementation
# Load new contextual collection (separate from original)
python load_pdf_qdrant.py --contextual --clear

# Test with NEW collection
export QDRANT_COLLECTION_NAME='tro-child-1-contextual'
python test_failed.py  # Uses tro-child-1-contextual (new)
# Output: Correct answer ($4,106 from BCY 2026)

# Compare batch evaluation results
python evaluation/batch_evaluator.py  # With contextual collection
# vs.
python evaluation/batch_evaluator.py  # With original collection
```

---

## Implementation Checklist

### Phase 1: Setup & Configuration (30 min)
- [ ] Add `GROQ_API_KEY` to environment/`.env` if not already set
- [ ] Read `chatbot/config.py` and confirm `openai/gpt-oss-20b` is the RAG model
- [ ] Create `LOAD_DB/prompts/` directory structure
- [ ] Update `LOAD_DB/config.py`:
  - Add `GROQ_MODEL = 'openai/gpt-oss-20b'` (use same model as RAG)
  - Add `QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1-contextual'` (new collection for comparison)
  - Add `CONTEXT_BATCH_SIZE = 10`
  - Add `CONTEXT_RATE_LIMIT_DELAY = 2` (seconds between batches)
  - Add `ENABLE_CONTEXTUAL_RETRIEVAL = True`

### Phase 2: Create Prompt Files (1 hour)
- [ ] Create `LOAD_DB/prompts/__init__.py` (empty or with exports)
- [ ] Create `LOAD_DB/prompts/master_context_prompt.py`:
  - `MASTER_CONTEXT` constant with static context string
- [ ] Create `LOAD_DB/prompts/document_context_prompt.py`:
  - `build_document_context_prompt(master_context, document_title, source_url, total_pages, first_2000_chars)` function
  - Returns formatted prompt for GROQ
- [ ] Create `LOAD_DB/prompts/chunk_context_prompt.py`:
  - `build_chunk_context_prompt(document_context, page_num, total_pages, chunk_index, total_chunks, chunk_text)` function
  - Returns formatted prompt for GROQ

### Phase 3: Create Contextual Processor Module (2-3 hours)
- [ ] Create `LOAD_DB/contextual_processor.py` with:
  - Imports from `prompts/` directory
  - `ContextualChunkProcessor` class
  - `generate_document_context(pdf_path, first_2000_chars)` - calls GROQ for Tier 2
  - `generate_chunk_contexts_batch(chunks, document_context)` - calls GROQ for Tier 3
  - Error handling with exponential backoff and retry logic
  - Logging at each step (context generation start/end, token counts)

### Phase 4: Integrate with PDF Loader (2-3 hours)
- [ ] Modify `LOAD_DB/load_pdf_qdrant.py`:
  - Add import: `from contextual_processor import ContextualChunkProcessor`
  - Add `--contextual` flag support to command-line arguments
  - In `__init__()`: Initialize `self.contextual_processor = ContextualChunkProcessor(groq_api_key, model)` (only if contextual enabled)
  - In `process_pdf()` after splitting documents:
    - Check cache for document context (only if contextual enabled)
    - If not cached: call `processor.generate_document_context(pdf_path, first_2000_chars)`
    - Save to cache file
  - In `upload_documents_to_qdrant()` **before** embedding (only if contextual enabled):
    - For each batch of 10 documents
    - Call `processor.generate_chunk_contexts_batch(batch, document_context)`
    - Prepend contexts to `doc.page_content`: `doc.page_content = f"{master_context}\n\n{document_context}\n\n{chunk_context}\n\n{original_content}"`
    - Add `has_context: True` to metadata
    - Include context token counts in logs
  - Use appropriate Qdrant collection name (`tro-child-1` vs `tro-child-1-contextual` based on `--contextual` flag)

### Phase 5: Test with Small Dataset (2-3 hours)
**IMPORTANT: Actual population and testing of Qdrant**

- [ ] Test with `--test --contextual` flags (3 PDFs, populate Qdrant):
  ```bash
  cd LOAD_DB
  python load_pdf_qdrant.py --test --contextual --clear
  ```
  - This populates `tro-child-1-contextual` collection with 3 PDF's worth of contextual chunks

- [ ] Inspect logs for:
  - Document context generation success (3 documents)
  - Chunk context generation timing and success rate
  - Any GROQ API errors or rate limiting issues
  - Context quality in logs

- [ ] Manually review generated contexts:
  - Read 5-10 contexts from logs
  - Verify they're informative and specific
  - Check that document contexts include key metrics/thresholds

- [ ] Run verification on contextual collection:
  ```bash
  cd LOAD_DB
  python verify_qdrant.py  # Should verify tro-child-1-contextual by default or with explicit flag
  ```
  - Check metadata: Verify `has_context: True` is set in all points
  - Check that contexts are prepended to chunk text
  - Count total chunks in collection (should match 3 PDFs)

- [ ] Sample random chunks and verify structure:
  ```bash
  # From Python REPL or simple script
  from qdrant_client import QdrantClient
  client = QdrantClient(url="...", api_key="...")
  points = client.scroll(collection_name="tro-child-1-contextual", limit=5)
  for point in points[0]:
      print(point.payload['text'][:500])  # Should show [Master] [Document] [Chunk] [Original]
  ```

### Phase 6: Validation on Failing Test (1 hour)
- [ ] Configure chatbot to use contextual collection:
  ```bash
  cd /home/tromanow/COHORT/TX
  export QDRANT_COLLECTION_NAME='tro-child-1-contextual'
  ```

- [ ] Run the failing test:
  ```bash
  python test_failed.py
  ```
  - Verify the chatbot answer now includes "$4,106 bi-weekly" (correct answer)
  - Check source document ranking (should be within top 20)

- [ ] Compare with original collection (for head-to-head):
  ```bash
  # Reset to original collection
  unset QDRANT_COLLECTION_NAME  # or export QDRANT_COLLECTION_NAME='tro-child-1'
  python test_failed.py
  # Compare answers and sources
  ```

### Phase 7: Full Pipeline Run (30-45 min)
- [ ] Run on all 37 PDFs with contextual generation:
  ```bash
  cd LOAD_DB
  python load_pdf_qdrant.py --contextual --clear
  ```
  - Estimated time: 30-45 minutes
  - Monitor logs for completion
  - Check for any GROQ API failures

- [ ] Verify full contextual collection:
  ```bash
  python verify_qdrant.py
  # Verify: ~740 chunks loaded, all with has_context: True
  ```

### Phase 8: Full Evaluation & Comparison (1-2 hours)
- [ ] Run batch evaluation on contextual collection:
  ```bash
  cd evaluation
  export QDRANT_COLLECTION_NAME='tro-child-1-contextual'
  python batch_evaluator.py > evaluation_contextual_results.txt
  ```

- [ ] Compare results with original collection:
  ```bash
  unset QDRANT_COLLECTION_NAME  # Reset to original
  python batch_evaluator.py > evaluation_original_results.txt
  ```

- [ ] Generate comparison report:
  - Composite score improvement (from 41.7/100 baseline)
  - Number of failing tests fixed
  - Retrieval ranking improvements for key test cases

---

## File Changes Summary

### Files to CREATE:
1. **`LOAD_DB/prompts/` (NEW DIRECTORY)**
   - `__init__.py` - Empty or with exports
   - `master_context_prompt.py` (~20 lines)
     - `MASTER_CONTEXT` constant: Static 50-token master context
   - `document_context_prompt.py` (~30 lines)
     - `build_document_context_prompt(master_context, document_title, source_url, total_pages, first_2000_chars)` function
   - `chunk_context_prompt.py` (~30 lines)
     - `build_chunk_context_prompt(document_context, page_num, total_pages, chunk_index, total_chunks, chunk_text)` function

2. **`LOAD_DB/contextual_processor.py`** (NEW, ~400-500 lines)
   - Imports from `prompts/` directory
   - `ContextualChunkProcessor` class
   - Document and chunk context generation
   - GROQ API integration with error handling
   - Logging and caching

### Files to MODIFY:
1. **`LOAD_DB/config.py`** (~10-15 lines added)
   - `GROQ_MODEL = 'openai/gpt-oss-20b'`
   - `QDRANT_COLLECTION_NAME_CONTEXTUAL = 'tro-child-1-contextual'`
   - `CONTEXT_BATCH_SIZE = 10`
   - `CONTEXT_RATE_LIMIT_DELAY = 2`
   - `ENABLE_CONTEXTUAL_RETRIEVAL = True`

2. **`LOAD_DB/load_pdf_qdrant.py`** (~80-100 lines modified)
   - Add `--contextual` command-line flag
   - Import `ContextualChunkProcessor`
   - Initialize processor (if `--contextual` enabled)
   - Add document context generation in `process_pdf()`
   - Add chunk context generation in `upload_documents_to_qdrant()`
   - Use correct collection name based on flag
   - Prepend all contexts before embedding

### Files to READ (reference only):
- `chatbot/config.py` - Confirm GROQ model name and API patterns
- `chatbot/generator.py` - Reference GROQ API call patterns
- `chatbot/intent_router.py` - Reference prompt formatting and error handling

---

## Prompt Tuning Notes

**Why these prompts work for your use case**:

1. **Master Context**: Sets domain boundaries - "Texas childcare assistance" narrows the semantic space vs. generic documents

2. **Document Context**: Includes key metrics explicitly - "Family of 5 maximum bi-weekly income is $4,106" helps LLM distinguish BCY 2026 from older 85% SMI documents

3. **Chunk Context**: Emphasizes "query match" - this helps the embedding match phrases like "family of 5," "bi-weekly," "maximum income"

**Why this fixes the failing test**:
- Current issue: BCY 2026 chunk ranks 24th (contains correct "$4,106")
- Root cause: Embedding scores based purely on semantic similarity; table-heavy content scores lower than verbose prose
- Solution: Adding context like "maximum bi-weekly income is $4,106" adds semantic richness to match the query "maximum income bi-weekly"
- Expected result: Correct chunk moves from rank 24 → rank 15-18 (within top 20 limit)

---

## Risk Assessment

**Low Risk**:
- Using existing GROQ model (`openai/gpt-oss-20b`) - already integrated
- GROQ_API_KEY already configured (used by chatbot)
- Caching prevents re-processing on failure
- Graceful degradation if context generation fails

**Moderate Risk**:
- API rate limiting at 30 req/min - but batch processing (10 chunks at a time with 2s delay) should stay within limits
- Long processing time for 37 PDFs (~15 minutes) - checkpoint system provides resume capability

**Mitigation**:
- Implement exponential backoff on 429 errors
- Cache document contexts to avoid re-generation
- Log all context generation success/failures
- Test with `--test` flag (3 PDFs) before full run

---

## Success Criteria

1. ✅ Prompt files created and organized in `LOAD_DB/prompts/` directory
2. ✅ Contextual processor module created with GROQ integration
3. ✅ New `tro-child-1-contextual` collection created (separate from original)
4. ✅ Test load (3 PDFs) completes successfully: `python load_pdf_qdrant.py --test --contextual --clear`
5. ✅ Verification confirms all test chunks have `has_context: True` and contexts prepended
6. ✅ `test_failed.py` with contextual collection returns correct answer: "$4,106 per pay period"
7. ✅ Head-to-head comparison: Original collection still returns "$3,918" (unchanged behavior)
8. ✅ BCY 2026 chunk moves into top 10 retrieval results (was rank 24) in contextual collection
9. ✅ Full pipeline (37 PDFs) completes successfully
10. ✅ Batch evaluation composite score improves on contextual collection (from 41.7/100 baseline)

---

## Estimated Timeline

- **Phase 1: Setup & Config**: 30 min
- **Phase 2: Create Prompt Files**: 1 hour
- **Phase 3: Contextual Processor Module**: 2-3 hours
- **Phase 4: PDF Loader Integration**: 2-3 hours
- **Phase 5: Test with Small Dataset** (3 PDFs + validation): 2-3 hours
- **Phase 6: Failing Test Validation**: 1 hour
- **Phase 7: Full Pipeline Run** (37 PDFs): 30-45 min
- **Phase 8: Full Evaluation & Comparison**: 1-2 hours

**Total**: ~12-16 hours of implementation and testing work (plus API call wait times)

---

## Next Steps After Approval

1. Phase 1: Setup configuration
2. Phase 2: Create prompt files in `LOAD_DB/prompts/`
3. Phase 3: Implement `contextual_processor.py`
4. Phase 4: Integrate into `load_pdf_qdrant.py` with `--contextual` flag
5. Phase 5: Run test suite to verify end-to-end with Qdrant population
6. Phase 6: Validate on failing test case
7. Phase 7: Run full pipeline
8. Phase 8: Compare results (head-to-head between original and contextual collections)
