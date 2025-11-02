"""
Prompts for contextual retrieval in LOAD_DB pipeline.

Exports:
- MASTER_CONTEXT: Static master context for all PDFs
- build_document_context_prompt: Function to build document-level context prompt
- build_chunk_context_prompt: Function to build chunk-level context prompt
"""

from .master_context_prompt import MASTER_CONTEXT
from .document_context_prompt import build_document_context_prompt
from .chunk_context_prompt import build_chunk_context_prompt

__all__ = [
    'MASTER_CONTEXT',
    'build_document_context_prompt',
    'build_chunk_context_prompt',
]
