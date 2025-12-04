# Plan: Vertex AI Agent Test Suite

## Overview

Create comprehensive tests for the Vertex AI Agent integration, mirroring the existing OpenAI Agent test patterns. The Vertex Agent handler (`vertex_agent_handler.py`) and evaluator (`vertex_evaluator.py`) have been implemented but lack test coverage.

## Test Files to Create

### 1. `tests/test_vertex_agent_api.py`

**Purpose**: API tests for Vertex Agent mode endpoints

**Pattern**: Mirror `tests/test_openai_agent_api.py`

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestVertexAgentModelsEndpoint` | `test_returns_200_with_structure` | Endpoint returns 200 with models list and default |
| | `test_returns_expected_models` | Should include Gemini model IDs (gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash) |
| | `test_models_have_id_and_name` | Each model has id and name fields |
| `TestVertexAgentChatEndpoint` | `test_returns_answer_and_sources` | Response includes answer, sources, session_id, timestamp, processing_time |
| `TestVertexAgentConversational` | `test_conversation_preserves_history` | Multi-turn conversation preserves context (Turn 1: CCS, Turn 2: "How do I apply for it?") |
| `TestVertexAgentErrorHandling` | `test_invalid_mode_returns_422` | Invalid mode value returns 422 |
| | `test_empty_question_returns_422` | Empty question with vertex_agent mode returns 422 |

**Skip condition**: `pytest.mark.skipif` if Google Cloud credentials not configured (check `GOOGLE_APPLICATION_CREDENTIALS` or ADC)

---

### 2. `tests/test_vertex_conversational.py`

**Purpose**: Unit tests for Vertex Agent conversational support with thread-scoped memory

**Pattern**: Mirror `tests/test_openai_conversational.py`

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestVertexAgentConversational` | `test_single_turn_stateless` | Single query works without thread_id (stateless mode) |
| | `test_single_turn_with_thread_id` | Single query with explicit thread_id |
| | `test_multi_turn_history_accumulation` | Follow-up queries accumulate conversation history |
| | `test_conversation_isolation` | Different threads maintain isolated history |
| | `test_clear_conversation` | Clearing conversation removes history |
| | `test_new_conversation_returns_unique_ids` | new_conversation() returns unique thread IDs |
| | `test_get_history_nonexistent_thread` | get_history() returns empty list for unknown thread |
| | `test_handle_without_thread_id_generates_new_id` | Each stateless call generates a new thread_id |

**Fixture**: Create `VertexAgentHandler` instance for each test

---

### 3. `tests/test_evaluation_e2e_vertex.py`

**Purpose**: End-to-end test for the Vertex Agent evaluation mode

**Pattern**: Mirror `tests/test_evaluation_e2e_openai.py`

| Test Function | Description |
|---------------|-------------|
| `test_evaluation_completes_successfully` | Evaluation runs without errors, "Evaluation complete!" in output |
| `test_artifacts_created` | All expected output files created (detailed_results.jsonl, evaluation_summary.json, evaluation_report.txt, run_info.txt) |
| `test_detailed_results_format` | detailed_results.jsonl has correct structure (required fields, scores) |
| `test_summary_statistics` | evaluation_summary.json has valid statistics (timestamp, total_evaluated, average_scores, performance) |
| `test_pass_rate_acceptable` | Sanity questions achieve minimum pass rate (MIN_PASS_SCORE = 60.0) |
| `test_no_checkpoint_left_on_success` | Checkpoint cleared after successful completion |

**Configuration**:
- MODE = "vertex"
- RUN_NAME = "TEST_VERTEX"
- SANITY_QA_FILE = "test-sanity-qa.md" (same as OpenAI)
- TIMEOUT = 600 (extended for API latency)

---

### 4. `tests/manual/conversational_benchmarks/run_vertex.py`

**Purpose**: Manual conversational intelligence benchmarks for Vertex Agent

**Pattern**: Mirror `tests/manual/conversational_benchmarks/run_openai.py`

| Function | Description |
|----------|-------------|
| `run_conversation(handler, test, thread_id)` | Run a single test conversation using VertexAgentHandler |
| `main()` | Initialize handler, run TESTS from test_definitions.py, save results to `results/conversational_benchmarks/vertex/` |

**Output**: `results/conversational_benchmarks/vertex/RUN_<timestamp>/results.json` and `report.txt`

---

## Implementation Checklist

### `tests/test_vertex_agent_api.py`
- [ ] Add `vertex_configured()` helper to check Google Cloud credentials
- [ ] Add `pytestmark` skip condition if credentials not configured
- [ ] Implement `TestVertexAgentModelsEndpoint` class
- [ ] Implement `TestVertexAgentChatEndpoint` class
- [ ] Implement `TestVertexAgentConversational` class
- [ ] Implement `TestVertexAgentErrorHandling` class

### `tests/test_vertex_conversational.py`
- [ ] Add skip condition for missing credentials
- [ ] Create pytest fixture for `VertexAgentHandler`
- [ ] Implement `TestVertexAgentConversational` class with all 8 test methods

### `tests/test_evaluation_e2e_vertex.py`
- [ ] Create `EvaluationResult` singleton class (runs evaluation once)
- [ ] Implement `get_eval_result()` helper
- [ ] Implement 6 test functions
- [ ] Implement `run_all_tests()` for direct execution

### `tests/manual/conversational_benchmarks/run_vertex.py`
- [ ] Add project root to path
- [ ] Import `VertexAgentHandler`
- [ ] Import `TESTS`, `save_results`, `write_report` from test_definitions
- [ ] Implement `run_conversation()` function
- [ ] Implement `main()` function

---

## Credential Check Pattern

```python
import os

def vertex_configured():
    """Check if Google Cloud credentials are configured."""
    # Check for explicit service account JSON
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        return True
    # ADC may be configured via gcloud CLI
    # Check if we can import and initialize vertexai without error
    try:
        import vertexai
        return True
    except Exception:
        return False
```

Alternative simpler check:
```python
def vertex_configured():
    """Check if Vertex AI environment is likely configured."""
    return bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('VERTEX_PROJECT_ID'))
```

---

## Key Differences from OpenAI Tests

| Aspect | OpenAI Agent | Vertex Agent |
|--------|--------------|--------------|
| Credential check | `OPENAI_API_KEY` | `GOOGLE_APPLICATION_CREDENTIALS` or ADC |
| Models endpoint | `/api/models/openai-agent` | `/api/models/vertex-agent` |
| Mode value | `'openai_agent'` | `'vertex_agent'` |
| Model parameter | `openai_agent_model` | `vertex_agent_model` |
| Expected models | gpt-4o-mini, gpt-5-nano | gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| Handler class | `OpenAIAgentHandler` | `VertexAgentHandler` |
| Evaluation mode | `'openai'` | `'vertex'` |

---

## Test Execution

```bash
# Run API tests (requires backend server + credentials)
pytest tests/test_vertex_agent_api.py -v

# Run conversational unit tests (requires credentials only)
pytest tests/test_vertex_conversational.py -v

# Run evaluation E2E test (requires credentials + Qdrant)
pytest tests/test_evaluation_e2e_vertex.py -v
# Or direct execution:
python tests/test_evaluation_e2e_vertex.py

# Run manual benchmarks (not part of pytest suite)
python tests/manual/conversational_benchmarks/run_vertex.py
```

---

## Update test_definitions.py (Optional)

Add vertex to `get_output_dir()` and `write_report()` if needed for the manual benchmark runner. Currently, the functions are generic and should work with `system='vertex'` parameter.

---

## Dependencies

Ensure `vertexai` is importable in test environment:
```
google-cloud-aiplatform>=1.50.0
vertexai>=1.50.0
```
