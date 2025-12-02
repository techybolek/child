"""Intent handlers for routing queries to appropriate subsystems"""

from .base import BaseHandler
from .rag_handler import RAGHandler
from .location_handler import LocationSearchHandler

__all__ = ['BaseHandler', 'RAGHandler', 'LocationSearchHandler']

# KendraHandler is optional - only available if langchain-aws is installed
try:
    from .kendra_handler import KendraHandler
    __all__.append('KendraHandler')
except ImportError:
    KendraHandler = None

# OpenAIAgentHandler is optional - only available if openai-agents is installed
try:
    from .openai_agent_handler import OpenAIAgentHandler
    __all__.append('OpenAIAgentHandler')
except ImportError:
    OpenAIAgentHandler = None
