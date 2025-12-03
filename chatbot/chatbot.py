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
                 provider=None, retrieval_mode=None, conversational_mode=None):
        """Initialize chatbot with LangGraph-based RAG pipeline.

        Args:
            llm_model: Optional model override for generation
            reranker_model: Optional model override for reranking
            intent_model: Optional model override for intent classification
            provider: Optional provider override ('groq' or 'openai')
            retrieval_mode: Optional retrieval mode override ('dense', 'hybrid', or 'kendra')
            conversational_mode: Optional override for conversational mode (None = use env var)
        """
        # Store model overrides to pass through state
        self.llm_model = llm_model
        self.reranker_model = reranker_model
        self.intent_model = intent_model
        self.provider = provider
        self.retrieval_mode = retrieval_mode

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
            "retrieval_mode_override": self.retrieval_mode,
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
            "retrieval_mode_override": self.retrieval_mode,
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

    def ask_stream(self, question: str, thread_id: str | None = None):
        """Stream response tokens, yielding (event_type, data) tuples.

        Runs pipeline up to rerank, then streams generation.
        For location_search intent, yields single 'done' event with template.

        Args:
            question: User's question
            thread_id: Conversation thread ID (only used in conversational mode)

        Yields:
            tuple: (event_type, data) where event_type is 'token', 'done', or 'error'
        """
        import re
        from langchain_core.messages import HumanMessage, AIMessage

        start_time = time.time()

        # Import nodes for direct invocation
        from .graph.nodes.classify import classify_node
        from .graph.nodes.retrieve import retrieve_node
        from .graph.nodes.rerank import rerank_node
        from .graph.nodes.reformulate import reformulate_node
        from .graph.nodes.location import location_node
        from .generator import ResponseGenerator

        # Generate thread ID for new conversations
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        # Build initial state
        state = {
            "query": question,
            "debug": False,
            "intent": None,
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "answer": None,
            "sources": [],
            "response_type": "",
            "action_items": [],
            "debug_info": None,
            # Model overrides
            "llm_model_override": self.llm_model,
            "reranker_model_override": self.reranker_model,
            "intent_model_override": self.intent_model,
            "provider_override": self.provider,
            "retrieval_mode_override": self.retrieval_mode,
        }

        # For conversational mode, load history and add current message
        messages = []
        if self.conversational_mode and self.memory:
            thread_config = self.memory.get_thread_config(thread_id)
            existing_state = self.graph.get_state(thread_config)
            messages = list(existing_state.values.get("messages", []))
            messages.append(HumanMessage(content=question))
            state["messages"] = messages
            state["reformulated_query"] = None

            # Run reformulation
            reformulate_result = reformulate_node(state)
            state.update(reformulate_result)

        # Classify intent
        classify_result = classify_node(state)
        state.update(classify_result)

        intent = state["intent"]

        # Handle location search - no streaming needed
        if intent == "location_search":
            location_result = location_node(state)
            state.update(location_result)

            # Update history if conversational
            if self.conversational_mode and self.memory:
                messages.append(AIMessage(content=state["answer"]))
                self._update_conversation_history(thread_id, messages)

            processing_time = round(time.time() - start_time, 2)
            yield ("done", {
                "answer": state["answer"],
                "sources": state["sources"],
                "response_type": state["response_type"],
                "action_items": state["action_items"],
                "session_id": thread_id,
                "processing_time": processing_time,
            })
            return

        # Information path: retrieve → rerank → stream generate
        retrieve_result = retrieve_node(state)
        state.update(retrieve_result)

        rerank_result = rerank_node(state)
        state.update(rerank_result)

        reranked_chunks = state["reranked_chunks"]

        # Handle empty chunks
        if not reranked_chunks:
            answer = "I couldn't find information about that. Try calling 1-800-862-5252."
            if self.conversational_mode and self.memory:
                messages.append(AIMessage(content=answer))
                self._update_conversation_history(thread_id, messages)

            processing_time = round(time.time() - start_time, 2)
            yield ("done", {
                "answer": answer,
                "sources": [],
                "response_type": "information",
                "action_items": [],
                "session_id": thread_id,
                "processing_time": processing_time,
            })
            return

        # Initialize generator for streaming
        provider = state.get("provider_override") or config.LLM_PROVIDER
        model = state.get("llm_model_override") or config.LLM_MODEL
        api_key = config.GROQ_API_KEY if provider == 'groq' else config.OPENAI_API_KEY

        generator = ResponseGenerator(
            api_key=api_key,
            provider=provider,
            model=model
        )

        # Format recent history for multi-hop reasoning (conversational mode)
        recent_history = None
        if self.conversational_mode and messages and len(messages) >= 2:
            recent_history = self._format_recent_history(messages)

        # Use reformulated query if available
        query = state.get("reformulated_query") or state["query"]

        # Stream tokens
        full_response = ""
        try:
            for token in generator.generate_stream(query, reranked_chunks, recent_history):
                full_response += token
                yield ("token", {"content": token})
        except Exception as e:
            yield ("error", {"message": str(e), "partial": True})
            return

        # Extract cited sources
        cited_doc_nums = set(re.findall(r'\[Doc\s*(\d+)\]', full_response))
        sources = []
        for doc_num in sorted(cited_doc_nums, key=int):
            idx = int(doc_num) - 1
            if 0 <= idx < len(reranked_chunks):
                chunk = reranked_chunks[idx]
                sources.append({
                    'doc': chunk['filename'],
                    'page': chunk['page'],
                    'url': chunk['source_url']
                })

        # Update conversation history
        if self.conversational_mode and self.memory:
            messages.append(AIMessage(content=full_response))
            self._update_conversation_history(thread_id, messages)

        processing_time = round(time.time() - start_time, 2)
        yield ("done", {
            "answer": full_response,
            "sources": sources,
            "response_type": "information",
            "action_items": [],
            "session_id": thread_id,
            "processing_time": processing_time,
        })

    def _update_conversation_history(self, thread_id: str, messages: list):
        """Update conversation history in checkpointer.

        Args:
            thread_id: Conversation thread ID
            messages: Updated list of messages
        """
        if not self.memory:
            return

        thread_config = self.memory.get_thread_config(thread_id)

        # Use graph.update_state to persist messages
        self.graph.update_state(
            thread_config,
            {"messages": messages}
        )

    def _format_recent_history(self, messages: list, max_turns: int = 3) -> str:
        """Format recent Q&A pairs for generator context.

        Args:
            messages: List of messages (including current HumanMessage)
            max_turns: Maximum number of Q&A pairs to include

        Returns:
            Formatted string of recent Q&A pairs
        """
        from langchain_core.messages import HumanMessage, AIMessage

        if len(messages) < 2:
            return ""

        # Skip the last message (current query)
        history_messages = messages[:-1]

        pairs = []
        i = 0
        while i < len(history_messages) - 1:
            if isinstance(history_messages[i], HumanMessage) and isinstance(history_messages[i + 1], AIMessage):
                human_content = history_messages[i].content
                ai_content = history_messages[i + 1].content
                if len(ai_content) > 500:
                    ai_content = ai_content[:500] + "..."
                pairs.append(f"Q: {human_content}\nA: {ai_content}")
                i += 2
            else:
                i += 1

        if not pairs:
            return ""

        return "\n\n".join(pairs[-max_turns:])
