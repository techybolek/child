# Feature Request: Backend API Test for Source URL Validation

**Date:** 2025-12-05
**Status:** Refined

## Overview
Add a unit test to verify that the `/api/chat` endpoint properly handles source URLs, including when `source_url` is None in Qdrant.

## Problem Statement
A bug was discovered where `source_url: None` in Qdrant caused a "can only concatenate str (not 'NoneType') to str" error. The fix (using `or ''` pattern) needs test coverage to prevent regression.

## Users & Stakeholders
- Primary Users: Developers maintaining the backend
- Permissions: None required (test suite)

## Functional Requirements
1. Test that API response sources have valid `url` field (string, not None)
2. Test covers both cases: sources with URLs and sources without URLs
3. Test verifies the fix doesn't break when source_url is properly populated

## Acceptance Criteria
- [ ] Test added to `tests/test_backend_api.py` in `TestSourceValidation` class
- [ ] Test verifies `source.url` is always a string (empty string or valid URL)
- [ ] Test passes with current fix in place
- [ ] Test would fail if fix is reverted (validates the `or ''` pattern)

## Technical Requirements
- **File:** `tests/test_backend_api.py`
- **Class:** `TestSourceValidation` (existing)
- **Method:** `test_source_url_is_valid_string`
- **Framework:** pytest (already in use)
- **Fixture:** `backend_server` (existing)

## Implementation

Add this test method to the existing `TestSourceValidation` class:

```python
def test_source_url_is_valid_string(self, backend_server):
    """Source URL must be a string (empty or valid URL), never None.

    Bug: Qdrant returning source_url=None caused string concatenation error.
    Fix: Retrievers use `or ''` pattern to convert None to empty string.
    """
    r = requests.post(
        f"{backend_server}/api/chat",
        json={"question": "What is CCS?"}
    )
    assert r.status_code == 200
    data = r.json()

    for source in data.get("sources", []):
        assert isinstance(source.get("url"), str), \
            f"Source URL must be string, got {type(source.get('url'))}: {source}"
        # URL should be either empty string or valid URL starting with http
        url = source.get("url", "")
        assert url == "" or url.startswith("http"), \
            f"Source URL should be empty or valid URL, got: {url}"
```

## Out of Scope
- Testing Qdrant data directly (covered by loader tests)
- Frontend URL rendering (already defensive)
- Integration tests with mocked None values

## Success Metrics
- Test passes in CI
- Test would catch regression if `or ''` fix is removed
