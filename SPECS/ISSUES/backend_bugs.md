# Backend API Bugs

Last tested: 2025-12-01

## Test Results Summary

**Status:** 16 passed, 0 failed

```
tests/test_backend_api.py: 16/16 passed (54.70s)
```

## Test Coverage

| Test Class | Tests | Status |
|------------|-------|--------|
| TestHealthEndpoint | 1 | PASSED |
| TestModelsEndpoint | 1 | PASSED |
| TestChatEndpoint | 3 | PASSED |
| TestRequestValidation | 3 | PASSED |
| TestConversationalMode | 2 | PASSED |
| TestRetrievalMode | 4 | PASSED |
| TestSourceValidation | 1 | PASSED |
| TestResponseHeaders | 1 | PASSED |

---

## BUG-001: Kendra Source Page Validation Failure

**Status:** FIXED (2025-12-01)
**Severity:** High
**Test:** `TestSourceValidation::test_kendra_source_page_is_valid_integer`

### Description

The Kendra retriever returned `page='N/A'` as a string, which failed the `Source` Pydantic model validation. The model expects `page` to be an integer.

### Fix Applied

**File:** `chatbot/kendra_retriever.py:72`

Changed:
```python
# Before
'page': doc.metadata.get('page', 'N/A'),

# After
'page': int(doc.metadata.get('page', 0)) if str(doc.metadata.get('page', '')).isdigit() else 0,
```

Now returns `0` (integer) when page info is unavailable from Kendra metadata.

---

## Notes

- Health, models, and chat endpoints functioning correctly
- Request validation working as expected
- Conversational mode history preservation verified
- Retrieval modes (dense, hybrid) operational
- Invalid retrieval mode correctly returns 400
