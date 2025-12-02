# Plan: Integrate OpenAI Agents as Proper Chatbot Mode

## Overview
Move OpenAI Agents SDK integration from `OAI_EXPERIMENT/` to the main chatbot as a first-class mode alongside hybrid/dense.

## Configuration
Two environment variables (minimal):
```bash
export OPENAI_VECTOR_STORE_ID="vs_69210129c50c81919a906d0576237ff5"  # Required - OpenAI vector store ID
export OPENAI_AGENT_MODEL="gpt-5-nano"   # Optional - defaults to gpt-5-nano
```

## Files to Create

### 1. `chatbot/handlers/openai_agent_handler.py`
New handler following existing patterns (like KendraHandler):
- Import `openai-agents` SDK components
- `OpenAIAgentHandler` class with `handle(query, debug)` method
- Async workflow wrapped with `asyncio.run()` for sync interface
- Parse structured response (ANSWER/SOURCES sections)
- Return standard dict: `{answer, sources, response_type, action_items}`
- Error handling and logging

## Files to Modify

### 2. `chatbot/config.py`
Add configuration:
```python
# OpenAI Agent Settings
OPENAI_VECTOR_STORE_ID = os.getenv('OPENAI_VECTOR_STORE_ID', '')
OPENAI_AGENT_MODEL = os.getenv('OPENAI_AGENT_MODEL', 'gpt-5-nano')
```

### 3. `chatbot/handlers/__init__.py`
Export the new handler:
```python
from .openai_agent_handler import OpenAIAgentHandler
```

### 4. `evaluation/openai_evaluator.py`
Update to use new handler instead of importing from OAI_EXPERIMENT:
```python
from chatbot.handlers import OpenAIAgentHandler

class OpenAIAgentEvaluator:
    def __init__(self):
        self.handler = OpenAIAgentHandler()

    def query(self, question, debug=False):
        response = self.handler.handle(question, debug=debug)
        return {
            'answer': response['answer'],
            'sources': response['sources'],
            'response_type': response['response_type'],
            'response_time': response.get('response_time', 0)
        }
```

### 5. `interactive_chat.py`
Add openai mode to CLI:
- Add 'openai' to `--mode` choices
- In `get_handler()`, add case for openai mode returning `OpenAIAgentHandler()`

## Implementation Steps

1. Create `chatbot/handlers/openai_agent_handler.py` with handler class
2. Add config variables to `chatbot/config.py`
3. Update `chatbot/handlers/__init__.py` exports
4. Update `evaluation/openai_evaluator.py` to use new handler
5. Update `interactive_chat.py` to support openai mode
6. Test: `python interactive_chat.py --mode openai`
7. Test: `python -m evaluation.run_evaluation --mode openai --limit 1`

## Cleanup

### Delete after implementation
- `OAI_EXPERIMENT/` - Entire directory (experimental code absorbed into handler)

## Files Reference
- `OAI_EXPERIMENT/agent1.py` - Source code to adapt (then delete)
- `chatbot/handlers/kendra_handler.py` - Pattern to follow
- `evaluation/kendra_evaluator.py` - Evaluator pattern to follow
