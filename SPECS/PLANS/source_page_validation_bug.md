# Plan: Source Page Validation Bug Test

## Bug Summary

When using Kendra retrieval mode, the backend returns a 500 error because Kendra sources contain `page: 'N/A'` (string) instead of an integer, which fails Pydantic validation for the `Source` model.

**Error:**
```
Error in chat endpoint: 1 validation error for Source
page
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='N/A', input_type=str]
```

## Root Cause

- `backend/api/models.py:62` defines `page: int` in the `Source` model
- Kendra retriever returns sources with `page: 'N/A'` when page info is unavailable
- The response serialization fails when constructing `ChatResponse`

## Test Plan

Add a test to `tests/test_backend_api.py` that:
1. Uses Kendra retrieval mode with conversational mode enabled
2. Verifies the response doesn't fail with a 500 error due to page validation
3. Validates that sources have proper page values (integers, not strings)

## Files to Modify

| File | Change |
|------|--------|
| `tests/test_backend_api.py` | Add `TestSourceValidation` class with test for non-integer page values |

## Test Implementation

```python
class TestSourceValidation:
    def test_kendra_source_page_is_valid_integer(self, backend_server):
        """Sources must have integer page values, not 'N/A' strings.

        Bug: Kendra retriever returns page='N/A' which fails Source model validation.
        This causes a 500 error instead of a successful response.
        """
        r = requests.post(
            f"{backend_server}/api/chat",
            json={
                "question": "what assistance can a family of 4 expect",
                "retrieval_mode": "kendra",
                "conversational_mode": True
            }
        )
        # Should not fail with 500 due to page validation
        if r.status_code == 200:
            data = r.json()
            for source in data.get("sources", []):
                assert isinstance(source["page"], int), \
                    f"Source page must be int, got {type(source['page'])}: {source['page']}"
        # If Kendra not configured, that's fine - but should NOT be a validation error
        elif r.status_code == 500:
            error_msg = r.json().get("detail", str(r.json()))
            assert "int_parsing" not in error_msg, \
                f"Source validation failed - page is not an integer: {error_msg}"
```

## Success Criteria

- [x] Test reproduces the bug (fails with current code)
- [ ] Test passes after fix is applied
- [ ] No other tests are affected

## Test Execution Result

```
FAILED tests/test_backend_api.py::TestSourceValidation::test_kendra_source_page_is_valid_integer
AssertionError: Source validation failed - page is likely not an integer:
{'message': 'Failed to generate response. Please try again.', 'error_type': 'ValidationError'}
```

The test successfully reproduces the bug.
