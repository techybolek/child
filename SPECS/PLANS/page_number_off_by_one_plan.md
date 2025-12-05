# Bug: Page Numbers Off-By-One in Cited Sources

## Bug Description
Page numbers displayed in cited sources are off by one. Users see page numbers starting at 0 (e.g., page 0, 1, 2...) when they expect human-readable 1-indexed page numbers (page 1, 2, 3...).

**Expected:** Source citation shows "page: 1" for the first page of a PDF
**Actual:** Source citation shows "page: 0" for the first page of a PDF

## Problem Statement
The internal page representation uses 0-indexed values (matching PyMuPDFLoader's output), but these raw values are exposed directly to users in API responses without conversion to human-readable 1-indexed format.

## Solution Statement
Convert 0-indexed page numbers to 1-indexed when building source citations for API responses. The fix should be applied at the source extraction layer where cited sources are assembled, not at the data loading layer. This preserves internal consistency while presenting user-friendly page numbers.

The conversion should use: `page + 1` for integer pages, preserving 'N/A' strings unchanged.

## Steps to Reproduce
1. Start the backend: `cd backend && python main.py`
2. Send a chat request: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"question": "What are the income limits for CCS?"}'`
3. Observe the `sources` array in the response
4. Note that page numbers start at 0 instead of 1

## Root Cause Analysis
Two extractors store 0-indexed page numbers:

1. **PyMuPDFLoader** (LangChain): Returns 0-indexed page metadata by default. This is documented behavior - the first page has `'page': 0`.

2. **Docling extractor** (`LOAD_DB/extractors/docling_extractor.py`): Intentionally converts to 0-indexed with `page_no - 1` at 6 locations (lines 93, 107, 127, 143, 157, 178) to match PyMuPDFLoader behavior.

The 0-indexed values are:
- Stored in Qdrant vector database
- Retrieved unchanged by `hybrid_retriever.py` and `retriever.py`
- Passed directly to source citations without conversion
- Returned to users in API responses

The source citation extraction happens in 3 places, all passing raw page values:
- `chatbot/graph/nodes/generate.py:119`
- `chatbot/chatbot.py:358`
- `chatbot/handlers/rag_handler.py:198`

## Relevant Files
Files that need modification to fix the bug:

- **chatbot/graph/nodes/generate.py** - LangGraph generate node builds sources dict at line 119. Add +1 conversion here.
- **chatbot/chatbot.py** - Streaming mode builds sources dict at line 358. Add +1 conversion here.
- **chatbot/handlers/rag_handler.py** - Legacy handler builds sources at line 198. Add +1 conversion here.
- **tests/test_backend_api.py** - Add regression test to verify page numbers are 1-indexed.

Files for reference only (no changes needed):
- `LOAD_DB/extractors/docling_extractor.py` - Source of 0-indexed pages (intentional, matches PyMuPDF)
- `LOAD_DB/extractors/pymupdf_extractor.py` - Uses LangChain's PyMuPDFLoader (0-indexed by design)
- `chatbot/hybrid_retriever.py` - Retrieves raw page values from Qdrant
- `chatbot/retriever.py` - Retrieves raw page values from Qdrant
- `backend/api/models.py` - Source model accepts `Union[int, str]` for page field

## Step by Step Tasks

### 1. Fix generate node (LangGraph pipeline)
- Edit `chatbot/graph/nodes/generate.py`
- At line 119 where `'page': chunk['page']` is set
- Change to: `'page': chunk['page'] + 1 if isinstance(chunk['page'], int) else chunk['page']`
- This handles both integer pages (convert) and 'N/A' strings (preserve)

### 2. Fix chatbot streaming mode
- Edit `chatbot/chatbot.py`
- At line 358 where `'page': chunk['page']` is set
- Change to: `'page': chunk['page'] + 1 if isinstance(chunk['page'], int) else chunk['page']`

### 3. Fix legacy RAG handler
- Edit `chatbot/handlers/rag_handler.py`
- At line 198 where `'page': chunks[idx]['page']` is set
- Change to: `'page': chunks[idx]['page'] + 1 if isinstance(chunks[idx]['page'], int) else chunks[idx]['page']`

### 4. Add regression test
- Edit `tests/test_backend_api.py`
- Add new test in `TestSourceValidation` class:
```python
def test_source_page_is_one_indexed(self, backend_server):
    """Page numbers must be 1-indexed (human-readable), not 0-indexed.

    Bug: Internal 0-indexed pages from PyMuPDF were exposed to users.
    Fix: Convert to 1-indexed when building source citations.
    """
    r = requests.post(
        f"{backend_server}/api/chat",
        json={"question": "What is CCS?"}
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()

    for source in data.get("sources", []):
        page = source.get("page")
        if isinstance(page, int):
            assert page >= 1, \
                f"Page numbers must be 1-indexed (>= 1), got {page}. Source: {source}"
```

### 5. Run validation commands
- Execute all validation commands to confirm the fix works with zero regressions

## Validation Commands
Execute every command to validate the bug is fixed with zero regressions.

```bash
# 1. Run the specific test class for source validation
cd /home/tromanow/COHORT/TX && python -m pytest tests/test_backend_api.py::TestSourceValidation -v

# 2. Run full backend API test suite
cd /home/tromanow/COHORT/TX && python -m pytest tests/test_backend_api.py -v

# 3. Manual verification - check page numbers in response
cd /home/tromanow/COHORT/TX/backend && timeout 30 python main.py &
sleep 5
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the income limits?"}' | python -c "import sys,json; d=json.load(sys.stdin); print('Pages:', [s['page'] for s in d.get('sources',[])])"
pkill -f "python main.py"

# 4. Verify pages are >= 1 (not 0)
# The output from command 3 should show pages like [1, 2, 3] not [0, 1, 2]
```

## Notes
- The fix is applied at the presentation layer (source extraction) rather than the data layer (loading). This keeps internal representation consistent and avoids requiring a full re-index of the vector database.
- The `isinstance(page, int)` check ensures 'N/A' string values are preserved unchanged.
- Three files need identical fixes because source extraction is duplicated across LangGraph pipeline, streaming mode, and legacy handler.
- Future refactoring could consolidate source extraction into a shared utility function, but that's out of scope for this bug fix.
