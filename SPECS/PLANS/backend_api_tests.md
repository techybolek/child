# Backend API Integration Tests

## Objective
Test backend-specific HTTP layer behavior with real chatbot (no mocking). Tests auto-launch backend on non-standard port, run tests, then shutdown.

## Scope

### Test (Backend-Specific)
| Category | Tests |
|----------|-------|
| HTTP Layer | Status codes, response structure, headers |
| Request Validation | Pydantic constraints → 422 errors |
| Response Formatting | session_id, timestamp, processing_time fields |
| Endpoints | `/api/health`, `/api/models`, `/api/chat` |

### Skip (Already Covered by Chatbot Tests)
- Answer quality, context resolution
- Conversational memory logic
- Query reformulation correctness

## Implementation

### 1. Modify `backend/config.py` (line 30)
```python
PORT = int(os.getenv("PORT", 8000))
```

### 2. Create `tests/conftest.py`
```python
import pytest
import subprocess
import time
import requests
import os

TEST_PORT = 8765
BASE_URL = f"http://localhost:{TEST_PORT}"

@pytest.fixture(scope="module")
def backend_server():
    """Launch backend on test port, yield, then shutdown."""
    env = os.environ.copy()
    env["PORT"] = str(TEST_PORT)

    proc = subprocess.Popen(
        ["python", "main.py"],
        cwd="backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server ready (poll health endpoint)
    for _ in range(15):  # 15s timeout
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=1)
            if r.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError("Backend failed to start")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)
```

### 3. Create `tests/test_backend_api.py`
```python
import pytest
import requests

RELIABLE_QUESTION = "What is CCS?"

class TestHealthEndpoint:
    def test_returns_200_with_status(self, backend_server):
        r = requests.get(f"{backend_server}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert "chatbot_initialized" in data
        assert data["chatbot_initialized"] is True

class TestModelsEndpoint:
    def test_returns_200_with_structure(self, backend_server):
        r = requests.get(f"{backend_server}/api/models")
        assert r.status_code == 200
        data = r.json()
        assert "provider" in data
        assert "generators" in data

class TestChatEndpoint:
    def test_valid_request_returns_200(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert "timestamp" in data
        assert "processing_time" in data
        assert data["processing_time"] > 0

    def test_session_id_generated_when_missing(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert r.status_code == 200
        assert r.json()["session_id"] is not None

    def test_session_id_preserved_when_provided(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION, "session_id": "test-123"}
        )
        assert r.status_code == 200
        assert r.json()["session_id"] == "test-123"

class TestRequestValidation:
    def test_empty_question_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": ""}
        )
        assert r.status_code == 422

    def test_question_too_long_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": "x" * 501}
        )
        assert r.status_code == 422

    def test_missing_question_returns_422(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={}
        )
        assert r.status_code == 422

class TestResponseHeaders:
    def test_process_time_header_present(self, backend_server):
        r = requests.post(
            f"{backend_server}/api/chat",
            json={"question": RELIABLE_QUESTION}
        )
        assert "x-process-time" in r.headers
```

## Files to Modify/Create

| File | Action |
|------|--------|
| `backend/config.py` | Modify PORT to read from env |
| `tests/conftest.py` | Create with backend_server fixture |
| `tests/test_backend_api.py` | Create with test classes |

## Run Command
```bash
pytest tests/test_backend_api.py -v
```

## Notes
- Uses `requests` (already in requirements.txt)
- Test port 8765 avoids conflict with dev server on 8000
- Module-scoped fixture means server starts once per test file
- 15s timeout for server startup
