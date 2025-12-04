# Kendra Handler Consolidation Plan

Consolidate Kendra usage by eliminating `KendraHandler` and using `KendraRetriever` through the LangGraph pipeline everywhere.

## Problem

Two parallel Kendra implementations exist:

| Path | Entry Point | Implementation | Conversational? | Reranking? |
|------|-------------|----------------|-----------------|------------|
| Legacy | `interactive_chat.py --mode kendra` | `KendraHandler` | No | No (correct) |
| Legacy | `evaluation --mode kendra` | `KendraEvaluator` → `KendraHandler` | No | No (correct) |
| LangGraph | Web UI/API with `retrieval_mode: 'kendra'` | `TexasChildcareChatbot` → `KendraRetriever` | Yes | Yes (wrong!) |

This causes:
- Code duplication (chunk conversion logic in two places)
- Inconsistent behavior (evaluation differs from production)
- Maintenance burden (two code paths to update)
- **LangGraph path incorrectly applies LLM reranking to Kendra results** (Kendra has built-in semantic ranking)

## Solution

1. Use `TexasChildcareChatbot(retrieval_mode='kendra')` everywhere
2. **Skip LLM reranking for Kendra mode** - Kendra already ranks results semantically

## Files to Modify

### 0. `chatbot/graph/nodes/rerank.py` (NEW - Critical)

**Skip reranking for Kendra** - Kendra has built-in semantic ranking, adding LLM reranking is redundant and potentially harmful.

**Current:** Always reranks all retrieved chunks.

**After:** Skip reranking when retrieval mode is `kendra`:

```python
def rerank_node(state: dict) -> dict:
    """Rerank chunks using LLM judge scoring.

    Skips reranking for Kendra mode (Kendra has built-in semantic ranking).
    """
    # Use reformulated query if available (conversational mode)
    query = state.get("reformulated_query") or state["query"]
    retrieved_chunks = state["retrieved_chunks"]
    debug = state.get("debug", False)

    # Handle empty retrieval
    if not retrieved_chunks:
        print("[Rerank Node] No chunks to rerank")
        return {"reranked_chunks": []}

    # Skip reranking for Kendra - it has built-in semantic ranking
    mode = state.get("retrieval_mode_override") or config.RETRIEVAL_MODE
    if mode == 'kendra':
        print(f"[Rerank Node] Skipping reranking for Kendra (built-in ranking)")
        # Just pass through retrieved chunks, limited to RERANK_TOP_K
        reranked_chunks = retrieved_chunks[:config.RERANK_TOP_K]
        result = {"reranked_chunks": reranked_chunks}
        if debug:
            debug_info = state.get("debug_info") or {}
            debug_info['reranker_skipped'] = True
            debug_info['reranker_skip_reason'] = 'Kendra has built-in semantic ranking'
            result["debug_info"] = debug_info
        return result

    # ... rest of existing reranking logic for hybrid/dense ...
```

### 1. `interactive_chat.py`

**Current:**
```python
def get_handler(mode: str):
    if mode == 'kendra':
        from chatbot.handlers.kendra_handler import KendraHandler
        return KendraHandler()
```

**After:**
```python
def get_handler(mode: str):
    if mode == 'kendra':
        return None  # Use chatbot with retrieval_mode override
```

Update main logic to use `TexasChildcareChatbot(retrieval_mode='kendra')` for kendra mode.

### 2. `evaluation/kendra_evaluator.py`

**Current:**
```python
from chatbot.handlers.kendra_handler import KendraHandler

class KendraEvaluator:
    def __init__(self):
        self.handler = KendraHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        response = self.handler.handle(question, debug=debug)
```

**After:**
```python
from chatbot.chatbot import TexasChildcareChatbot

class KendraEvaluator:
    def __init__(self):
        self.chatbot = TexasChildcareChatbot(
            retrieval_mode='kendra',
            conversational_mode=False  # Evaluation is single-turn
        )

    def query(self, question: str, debug: bool = False) -> dict:
        response = self.chatbot.ask(question, debug=debug)
```

### 3. `chatbot/handlers/__init__.py`

**Current:**
```python
try:
    from .kendra_handler import KendraHandler
    __all__.append('KendraHandler')
except ImportError:
    KendraHandler = None
```

**After:**
Remove the `KendraHandler` import block entirely.

### 4. Files to Delete

| File | Reason |
|------|--------|
| `chatbot/handlers/kendra_handler.py` | Replaced by LangGraph pipeline |
| `chatbot/handlers/kendra_handler.py.backup` | Obsolete backup |
| `test_kendra_rearchitecture.py` | Tests deleted handler |

## Implementation Steps

### Step 1: Update `evaluation/kendra_evaluator.py`

Replace `KendraHandler` with `TexasChildcareChatbot`:

```python
"""Kendra evaluator using unified LangGraph pipeline"""

import time
from chatbot.chatbot import TexasChildcareChatbot


class KendraEvaluator:
    """Evaluator that uses Kendra retrieval through LangGraph pipeline"""

    def __init__(self):
        self.chatbot = TexasChildcareChatbot(
            retrieval_mode='kendra',
            conversational_mode=False
        )

    def query(self, question: str, debug: bool = False) -> dict:
        """Query Kendra-based chatbot and return response with timing"""
        start_time = time.time()
        response = self.chatbot.ask(question, debug=debug)
        response_time = time.time() - start_time

        result = {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response_time
        }

        if debug and 'debug_info' in response:
            result['debug_info'] = response['debug_info']

        return result
```

### Step 2: Update `interactive_chat.py`

Simplify handler logic:

```python
def get_handler(mode: str):
    """Get appropriate handler based on mode"""
    if mode == 'openai':
        from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler
        return OpenAIAgentHandler()
    else:
        # All other modes (hybrid, dense, kendra) use chatbot
        return None


def main():
    # ... existing argument parsing ...

    if mode == 'openai':
        handler = get_handler(mode)
        chatbot = None
    else:
        # Use TexasChildcareChatbot for hybrid, dense, AND kendra
        chatbot = TexasChildcareChatbot(retrieval_mode=mode)
        handler = None
```

### Step 3: Update `chatbot/handlers/__init__.py`

Remove KendraHandler:

```python
"""Intent handlers for routing queries to appropriate subsystems"""

from .base import BaseHandler
from .rag_handler import RAGHandler
from .location_handler import LocationSearchHandler

__all__ = ['BaseHandler', 'RAGHandler', 'LocationSearchHandler']

# OpenAIAgentHandler is optional - only available if openai-agents is installed
try:
    from .openai_agent_handler import OpenAIAgentHandler
    __all__.append('OpenAIAgentHandler')
except ImportError:
    OpenAIAgentHandler = None
```

### Step 4: Delete obsolete files

```bash
rm chatbot/handlers/kendra_handler.py
rm chatbot/handlers/kendra_handler.py.backup
rm test_kendra_rearchitecture.py
```

### Step 5: Update tests

Update `tests/test_kendra_retriever.py` to remove any `KendraHandler` references (none currently exist - tests already use `KendraRetriever` and `TexasChildcareChatbot`).

## Regression Tests

### Existing Tests to Run

| Test File | Command | Notes |
|-----------|---------|-------|
| `test_kendra_retriever.py` | `pytest tests/test_kendra_retriever.py -v` | Already uses `TexasChildcareChatbot` |
| `test_evaluation_e2e_kendra.py` | `pytest tests/test_evaluation_e2e_kendra.py -v` | Will work after migration |
| `test_backend_api.py` | `pytest tests/test_backend_api.py -v` | Has Kendra API tests |
| `test_conversational_rag.py` | `pytest tests/test_conversational_rag.py -v` | Memory/reformulation |

### CLI Manual Tests
```bash
# Test interactive_chat.py with all modes
python interactive_chat.py --mode kendra "What is CCS?"
python interactive_chat.py --mode hybrid "What is CCS?"
python interactive_chat.py --mode dense "What is CCS?"
```

### Evaluation Framework
```bash
# Quick sanity check for all modes
python -m evaluation.run_evaluation --mode kendra --test --limit 3
python -m evaluation.run_evaluation --mode hybrid --test --limit 3
python -m evaluation.run_evaluation --mode dense --test --limit 3
```

---

## New Tests to Create

### 1. `tests/test_kendra_retriever.py` - Add rerank skip test

Add to `TestKendraInPipeline` class:

```python
def test_kendra_skips_reranking(self):
    """Verify reranking is skipped for Kendra mode (Kendra has built-in ranking)."""
    from chatbot.chatbot import TexasChildcareChatbot

    chatbot = TexasChildcareChatbot(retrieval_mode='kendra')
    result = chatbot.ask("What is CCS?", debug=True)

    assert 'answer' in result
    debug_info = result.get('debug_info', {})

    # Verify reranking was skipped
    assert debug_info.get('reranker_skipped') is True, \
        "Expected reranker to be skipped for Kendra mode"
    assert 'built-in' in debug_info.get('reranker_skip_reason', '').lower(), \
        "Expected skip reason to mention built-in ranking"

    print("✓ Kendra correctly skips LLM reranking")
```

### 2. `tests/test_kendra_retriever.py` - Add conversational mode test

Add to `TestKendraInPipeline` class:

```python
def test_kendra_with_conversational_mode(self):
    """Verify Kendra works with conversational mode (reformulation + memory)."""
    from chatbot.chatbot import TexasChildcareChatbot

    chatbot = TexasChildcareChatbot(
        retrieval_mode='kendra',
        conversational_mode=True
    )
    thread_id = chatbot.new_conversation()

    # Turn 1: Establish context
    r1 = chatbot.ask("What is CCS?", thread_id=thread_id)
    assert 'answer' in r1
    assert r1['turn_count'] == 1

    # Turn 2: Follow-up with pronoun
    r2 = chatbot.ask("How do I apply for it?", thread_id=thread_id)
    assert 'answer' in r2
    assert r2['turn_count'] == 2

    # Reformulated query should reference CCS
    reformulated = r2.get('reformulated_query', '')
    assert 'CCS' in reformulated or 'Child Care' in reformulated, \
        f"Expected CCS in reformulated query, got: {reformulated}"

    print("✓ Kendra + conversational mode works correctly")
```

### 3. `tests/test_kendra_retriever.py` - Add rerank NOT skipped for hybrid/dense

Add to `TestRetrievalModeRouting` class:

```python
def test_hybrid_does_not_skip_reranking(self):
    """Verify reranking is NOT skipped for hybrid mode."""
    from chatbot.chatbot import TexasChildcareChatbot

    chatbot = TexasChildcareChatbot(retrieval_mode='hybrid')
    result = chatbot.ask("What is CCS?", debug=True)

    assert 'answer' in result
    debug_info = result.get('debug_info', {})

    # Verify reranking was NOT skipped
    assert debug_info.get('reranker_skipped') is not True, \
        "Reranking should NOT be skipped for hybrid mode"
    # Should have reranker scores
    assert 'reranker_scores' in debug_info or 'final_chunks' in debug_info, \
        "Expected reranker output in debug info"

    print("✓ Hybrid mode correctly applies LLM reranking")

def test_dense_does_not_skip_reranking(self):
    """Verify reranking is NOT skipped for dense mode."""
    from chatbot.chatbot import TexasChildcareChatbot

    chatbot = TexasChildcareChatbot(retrieval_mode='dense')
    result = chatbot.ask("What is CCS?", debug=True)

    assert 'answer' in result
    debug_info = result.get('debug_info', {})

    # Verify reranking was NOT skipped
    assert debug_info.get('reranker_skipped') is not True, \
        "Reranking should NOT be skipped for dense mode"

    print("✓ Dense mode correctly applies LLM reranking")
```

---

## Test Checklist

| Test | Command | Expected Result |
|------|---------|-----------------|
| KendraRetriever initializes | `pytest tests/test_kendra_retriever.py::TestKendraRetriever::test_kendra_retriever_initializes -v` | Pass |
| KendraRetriever search format | `pytest tests/test_kendra_retriever.py::TestKendraRetriever::test_kendra_search_returns_correct_structure -v` | Pass |
| Chatbot with Kendra returns response | `pytest tests/test_kendra_retriever.py::TestKendraInPipeline::test_chatbot_with_kendra_returns_valid_response -v` | Pass |
| Kendra via retrieval_mode override | `pytest tests/test_kendra_retriever.py::TestKendraInPipeline::test_kendra_via_retrieval_mode_override -v` | Pass |
| **NEW: Kendra skips reranking** | `pytest tests/test_kendra_retriever.py::TestKendraInPipeline::test_kendra_skips_reranking -v` | Pass |
| **NEW: Kendra + conversational** | `pytest tests/test_kendra_retriever.py::TestKendraInPipeline::test_kendra_with_conversational_mode -v` | Pass |
| Retrieve node routes to Kendra | `pytest tests/test_kendra_retriever.py::TestRetrievalModeRouting::test_retrieve_node_routes_to_kendra -v` | Pass |
| **NEW: Hybrid doesn't skip rerank** | `pytest tests/test_kendra_retriever.py::TestRetrievalModeRouting::test_hybrid_does_not_skip_reranking -v` | Pass |
| **NEW: Dense doesn't skip rerank** | `pytest tests/test_kendra_retriever.py::TestRetrievalModeRouting::test_dense_does_not_skip_reranking -v` | Pass |
| Kendra evaluation E2E | `pytest tests/test_evaluation_e2e_kendra.py -v` | All pass |
| Conversational memory | `pytest tests/test_conversational_rag.py::TestConversationalMemory -v` | All pass |
| Query reformulation | `pytest tests/test_conversational_rag.py::TestQueryReformulation -v` | All pass |
| Backend API (includes Kendra) | `pytest tests/test_backend_api.py -v` | All pass |

## Behavioral Changes

After consolidation:

| Behavior | Before | After |
|----------|--------|-------|
| Kendra evaluation includes reranking | No | No (skipped) |
| Kendra CLI includes reranking | No | No (skipped) |
| Kendra Web UI includes reranking | Yes (bug!) | No (fixed) |
| Kendra evaluation matches production | No | Yes |
| Kendra CLI supports conversational | No | Could (if desired) |

**Note:** This fix also corrects the current LangGraph/Web UI path which incorrectly applies LLM reranking to Kendra results. Kendra has built-in semantic ranking - adding another reranking step is redundant.

## Rollback Plan

If issues arise, revert the changes to:
- `chatbot/graph/nodes/rerank.py`
- `interactive_chat.py`
- `evaluation/kendra_evaluator.py`
- `chatbot/handlers/__init__.py`

And restore deleted files from git.

## Success Criteria

1. All regression tests pass
2. `python -m evaluation.run_evaluation --mode kendra --test --limit 3` completes successfully
3. `python interactive_chat.py --mode kendra "What is CCS?"` returns valid answer
4. No references to `KendraHandler` remain in active code (only in SPECS/docs)
