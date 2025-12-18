"""
Shared PDF processing utilities for document cleaning, filtering, and metadata enrichment.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from text_cleaner import clean_text, is_likely_toc

logger = logging.getLogger(__name__)


def clean_documents(documents: List[Document]) -> List[Document]:
    """
    Clean page content in all documents using text_cleaner.

    Args:
        documents: List of Document objects

    Returns:
        Same documents with cleaned page_content
    """
    for doc in documents:
        doc.page_content = clean_text(doc.page_content)
    return documents


def filter_toc_chunks(documents: List[Document]) -> Tuple[List[Document], int]:
    """
    Filter out table of contents and structural metadata chunks.

    Args:
        documents: List of Document objects

    Returns:
        Tuple of (filtered_documents, filtered_count)
    """
    filtered_docs = []
    filtered_count = 0

    for doc in documents:
        if not is_likely_toc(doc.page_content):
            filtered_docs.append(doc)
        else:
            filtered_count += 1
            logger.debug(f"Filtered out TOC chunk: {doc.page_content[:100]}...")

    return filtered_docs, filtered_count


def add_chunk_metadata(documents: List[Document]) -> List[Document]:
    """
    Add chunk_index and total_chunks to metadata.

    Args:
        documents: List of Document objects

    Returns:
        Same documents with enriched metadata
    """
    total_chunks = len(documents)
    for i, doc in enumerate(documents):
        doc.metadata['chunk_index'] = i
        doc.metadata['total_chunks'] = total_chunks
    return documents


def enrich_metadata(
    documents: List[Document],
    pdf_filename: str,
    metadata_json: Optional[Dict[str, Any]] = None,
    total_pages: Optional[int] = None
) -> List[Document]:
    """
    Enrich document metadata with filename, content type, and optional metadata from JSON.

    Args:
        documents: List of Document objects
        pdf_filename: Name of the PDF file
        metadata_json: Optional metadata dictionary from JSON file
        total_pages: Optional total page count

    Returns:
        Same documents with enriched metadata
    """
    for doc in documents:
        # Add filename and content type
        doc.metadata['filename'] = pdf_filename
        doc.metadata['content_type'] = 'pdf'

        # Add metadata from JSON if available
        if metadata_json:
            doc.metadata.update({
                'source_url': metadata_json.get('source_url', ''),
                'pdf_id': metadata_json.get('pdf_id', ''),
                'file_size_mb': metadata_json.get('file_size_mb', 0),
            })

        # Add total pages if provided
        if total_pages is not None:
            doc.metadata['total_pages'] = total_pages
        elif metadata_json and 'page_count' in metadata_json:
            doc.metadata['total_pages'] = metadata_json['page_count']

    return documents
