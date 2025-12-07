# Plan: Make Evaluation Use LangGraph Pipeline

## Problem
- `ChatbotEvaluator` uses `RAGHandler` directly
- The chatbot (interactive_chat.py, backend) uses `TexasChildcareChatbot` (LangGraph)
- Different code paths - evaluation isn't testing what users actually use

## Solution
Make `ChatbotEvaluator` follow the same pattern as `KendraEvaluator`.

## File: `evaluation/evaluator.py`

Replace entire file with:

```python
"""Chatbot evaluator using LangGraph pipeline"""

import time
from chatbot.chatbot import TexasChildcareChatbot


class ChatbotEvaluator:
    def __init__(self, collection_name=None, retrieval_top_k=None, retrieval_mode=None):
        # collection_name and retrieval_top_k use config defaults
        self.chatbot = TexasChildcareChatbot(
            retrieval_mode=retrieval_mode,
            conversational_mode=False
        )

    def query(self, question: str, debug: bool = False) -> dict:
        """Query chatbot and return response with timing"""
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

## Note on Unused Parameters
- `collection_name` and `retrieval_top_k` are kept in constructor signature for backward compatibility
- They use config defaults (same behavior as before in practice)

## Testing
```bash
python -m evaluation.run_evaluation --mode hybrid --limit 3 --debug
```
