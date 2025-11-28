"""
Memory management for conversational RAG pipeline.

Provides thread-scoped conversation memory using LangGraph checkpointers.
"""

from langgraph.checkpoint.memory import MemorySaver


class MemoryManager:
    """Thread-scoped conversation memory.

    Manages conversation state across turns using LangGraph's checkpointer system.
    Each thread_id maintains its own isolated conversation history.
    """

    def __init__(self, backend: str = "memory"):
        """Initialize memory manager.

        Args:
            backend: Storage backend - "memory" for in-memory (default).
                     Future: "postgres" for production persistence.
        """
        if backend == "memory":
            self.checkpointer = MemorySaver()
        else:
            raise ValueError(f"Unknown backend: {backend}. Supported: 'memory'")

    def get_thread_config(self, thread_id: str) -> dict:
        """Get LangGraph config for a conversation thread.

        Args:
            thread_id: Unique identifier for the conversation thread.

        Returns:
            Config dict for graph.invoke() with thread_id configured.
        """
        return {"configurable": {"thread_id": thread_id}}
