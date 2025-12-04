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
