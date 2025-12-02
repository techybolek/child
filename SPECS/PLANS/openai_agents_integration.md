# Plan: Integrate OpenAI Agents as Proper Chatbot Mode

## Overview
Move OpenAI Agents SDK integration from `OAI_EXPERIMENT/` to the main chatbot as a first-class mode alongside hybrid/dense/kendra.

## Architecture Note

Unlike Kendra which has two integration paths:
- `KendraRetriever` - Drop-in retriever for LangGraph pipeline (retrieve → rerank → generate)
- `KendraHandler` - Standalone handler bypassing LangGraph

OpenAI Agents only needs a **handler** because the SDK is a self-contained RAG system with its own:
- Vector store (FileSearchTool)
- Retrieval
- Generation
- Reasoning

The agent handles everything internally and returns structured output.

## Configuration
Two environment variables (minimal):
```bash
export OPENAI_VECTOR_STORE_ID="vs_69210129c50c81919a906d0576237ff5"  # Required - OpenAI vector store ID
export OPENAI_AGENT_MODEL="gpt-5-nano"   # Optional - defaults to gpt-5-nano
```

## Files to Create

### 1. `chatbot/handlers/openai_agent_handler.py`
New handler following upgraded Kendra patterns:
- Inherit from `BaseHandler`
- `handle(query: str, debug: bool = False)` signature
- Import `openai-agents` SDK components (Agent, Runner, FileSearchTool, etc.)
- Async workflow wrapped with `asyncio.run()` for sync interface
- Parse structured response (ANSWER/SOURCES sections)
- Return standard dict: `{answer, sources, response_type, action_items}`
- Debug info: include agent trace/reasoning if available
- Error handling with fallback message

```python
class OpenAIAgentHandler(BaseHandler):
    def __init__(self):
        # Initialize FileSearchTool with vector store
        # Initialize Agent with model settings

    def handle(self, query: str, debug: bool = False) -> dict:
        # Run async workflow with asyncio.run()
        # Parse ANSWER/SOURCES sections
        # Return standardized response

    def _parse_response(self, output_text: str) -> tuple[str, list]:
        # Extract answer and sources from structured output
```

## Files to Modify

### 2. `chatbot/config.py`
Add configuration:
```python
# OpenAI Agent Settings
OPENAI_VECTOR_STORE_ID = os.getenv('OPENAI_VECTOR_STORE_ID', '')
OPENAI_AGENT_MODEL = os.getenv('OPENAI_AGENT_MODEL', 'gpt-5-nano')
```

### 3. `chatbot/handlers/__init__.py`
Add optional import (same pattern as Kendra):
```python
# OpenAIAgentHandler is optional - only available if openai-agents is installed
try:
    from .openai_agent_handler import OpenAIAgentHandler
    __all__.append('OpenAIAgentHandler')
except ImportError:
    OpenAIAgentHandler = None
```

### 4. `evaluation/openai_evaluator.py`
Update to match KendraEvaluator pattern exactly:
```python
import time
from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler


class OpenAIAgentEvaluator:
    def __init__(self):
        self.handler = OpenAIAgentHandler()

    def query(self, question: str, debug: bool = False) -> dict:
        start_time = time.time()
        response = self.handler.handle(question, debug=debug)
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

### 5. `interactive_chat.py`
Add openai mode to CLI:
```python
parser.add_argument('--mode', type=str, choices=['hybrid', 'dense', 'kendra', 'openai'],
                    help='Retrieval mode (default: from RETRIEVAL_MODE env or config)')

def get_handler(mode: str):
    if mode == 'kendra':
        from chatbot.handlers.kendra_handler import KendraHandler
        return KendraHandler()
    elif mode == 'openai':
        from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler
        return OpenAIAgentHandler()
    else:
        return None
```

## Implementation Steps

1. Create `chatbot/handlers/openai_agent_handler.py` with handler class
2. Add config variables to `chatbot/config.py`
3. Update `chatbot/handlers/__init__.py` exports (optional import pattern)
4. Update `evaluation/openai_evaluator.py` to use new handler
5. Update `interactive_chat.py` to support openai mode
6. Test: `python interactive_chat.py --mode openai`
7. Test: `python -m evaluation.run_evaluation --mode openai --limit 1`

## Cleanup

### Delete after implementation
- `OAI_EXPERIMENT/` - Entire directory (experimental code absorbed into handler)

## Files Reference
- `OAI_EXPERIMENT/agent1.py` - Source code to adapt (then delete)
- `chatbot/handlers/kendra_handler.py` - Handler pattern to follow
- `chatbot/handlers/base.py` - Base class to inherit
- `evaluation/kendra_evaluator.py` - Evaluator pattern to follow
