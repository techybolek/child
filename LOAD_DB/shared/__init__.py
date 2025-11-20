"""
Shared utilities for PDF processing and Qdrant uploading.
"""

from .pdf_processor import (
    clean_documents,
    filter_toc_chunks,
    add_chunk_metadata,
    enrich_metadata
)
from .qdrant_uploader import upload_with_embeddings

__all__ = [
    'clean_documents',
    'filter_toc_chunks',
    'add_chunk_metadata',
    'enrich_metadata',
    'upload_with_embeddings'
]
