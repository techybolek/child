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

# VertexAgentHandler is optional - only available if vertexai is installed
try:
    from .vertex_agent_handler import VertexAgentHandler
    __all__.append('VertexAgentHandler')
except ImportError:
    VertexAgentHandler = None
