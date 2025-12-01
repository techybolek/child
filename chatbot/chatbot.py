"""Texas Childcare RAG Chatbot with optional conversational memory."""

import time
import uuid

from . import config
from .graph.builder import build_graph


class TexasChildcareChatbot:
    """RAG chatbot - stateless or conversational based on config.

    When CONVERSATIONAL_MODE=False (default):
        - Single-turn RAG pipeline
        - No memory between calls

    When CONVERSATIONAL_MODE=True:
        - Multi-turn conversations with thread-scoped memory
        - Each thread maintains its own conversation history
    """

    def __init__(self, llm_model=None, reranker_model=None, intent_model=None,
                 provider=None, conversational_mode=None):
        """Initialize chatbot with LangGraph-based RAG pipeline.

        Args:
            llm_model: Optional model override for generation
            reranker_model: Optional model override for reranking
            intent_model: Optional model override for intent classification
            provider: Optional provider override ('groq' or 'openai')
            conversational_mode: Optional override for conversational mode (None = use env var)
        """
        # Store model overrides to pass through state
        self.llm_model = llm_model
        self.reranker_model = reranker_model
        self.intent_model = intent_model
        self.provider = provider

        # Explicit param takes precedence, otherwise use env var
        self.conversational_mode = (conversational_mode
                                    if conversational_mode is not None
                                    else config.CONVERSATIONAL_MODE)

        if self.conversational_mode:
            from .memory import MemoryManager
            self.memory = MemoryManager()
            self.graph = build_graph(checkpointer=self.memory.checkpointer)
            print("✓ Chatbot instance created (LangGraph with memory)")
        else:
            self.memory = None
            self.graph = build_graph()
            print("✓ Chatbot instance created (LangGraph)")

    def ask(self, question: str, thread_id: str | None = None, debug: bool = False) -> dict:
        """Ask a question, route through LangGraph pipeline.

        Args:
            question: User's question
            thread_id: Conversation thread ID (only used in conversational mode)
            debug: Enable debug output with retrieval/reranking details

        Returns:
            dict with answer, sources, response_type, action_items, processing_time
            In conversational mode, also includes: thread_id, turn_count, reformulated_query
        """
        if self.conversational_mode:
            return self._ask_conversational(question, thread_id, debug)
        else:
            return self._ask_stateless(question, debug)

    def _ask_stateless(self, question: str, debug: bool) -> dict:
        """Original single-turn behavior (stateless)."""
        start_time = time.time()

        initial_state = {
            "query": question,
            "debug": debug,
            "intent": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "answer": None,
            "sources": [],
            "response_type": "",
            "action_items": [],
            "debug_info": {} if debug else None,
            # Model overrides (nodes check these before falling back to config)
            "llm_model_override": self.llm_model,
            "reranker_model_override": self.reranker_model,
            "intent_model_override": self.intent_model,
            "provider_override": self.provider,
        }

        final_state = self.graph.invoke(initial_state)

        result = {
            'answer': final_state['answer'],
            'sources': final_state['sources'],
            'response_type': final_state['response_type'],
            'action_items': final_state.get('action_items', []),
        }

        if debug:
            result['debug_info'] = final_state.get('debug_info', {})

        result['processing_time'] = round(time.time() - start_time, 2)

        return result

    def _ask_conversational(self, question: str, thread_id: str | None, debug: bool) -> dict:
        """Multi-turn with memory."""
        from langchain_core.messages import HumanMessage

        start_time = time.time()

        # Generate thread ID for new conversations
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        thread_config = self.memory.get_thread_config(thread_id)

        input_state = {
            "messages": [HumanMessage(content=question)],
            "query": question,
            "reformulated_query": None,
            "debug": debug,
            "intent": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "answer": None,
            "sources": [],
            "response_type": "",
            "action_items": [],
            "debug_info": {} if debug else None,
            # Model overrides (nodes check these before falling back to config)
            "llm_model_override": self.llm_model,
            "reranker_model_override": self.reranker_model,
            "intent_model_override": self.intent_model,
            "provider_override": self.provider,
        }

        final_state = self.graph.invoke(input_state, thread_config)

        # Count turns (each turn = 1 user message + 1 assistant message)
        messages = final_state.get("messages", [])
        turn_count = len(messages) // 2

        result = {
            'answer': final_state['answer'],
            'sources': final_state['sources'],
            'response_type': final_state['response_type'],
            'action_items': final_state.get('action_items', []),
            'thread_id': thread_id,
            'turn_count': turn_count,
            'reformulated_query': final_state.get('reformulated_query'),
        }

        if debug:
            result['debug_info'] = final_state.get('debug_info', {})

        result['processing_time'] = round(time.time() - start_time, 2)

        return result

    def new_conversation(self) -> str:
        """Start a new conversation thread.

        Returns:
            New thread_id for the conversation
        """
        return str(uuid.uuid4())

    def get_history(self, thread_id: str) -> list[dict]:
        """Get conversation history for a thread.

        Args:
            thread_id: Conversation thread ID

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        if not self.conversational_mode or self.memory is None:
            return []

        from langchain_core.messages import HumanMessage

        thread_config = self.memory.get_thread_config(thread_id)
        state = self.graph.get_state(thread_config)

        messages = state.values.get("messages", [])
        return [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.content
            }
            for m in messages
        ]
