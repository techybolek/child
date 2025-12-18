"""
PDF extractor factory - selects appropriate extractor based on PDF type.
"""

import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .pymupdf_extractor import PyMuPDFExtractor
from .docling_extractor import DoclingExtractor
import config


def get_extractor(pdf_filename: str, text_splitter: RecursiveCharacterTextSplitter):
    """
    Get appropriate PDF extractor based on PDF type.

    Args:
        pdf_filename: Name of the PDF file (e.g., 'document.pdf')
        text_splitter: Text splitter for chunking (used by Docling for large narrative items)

    Returns:
        PyMuPDFExtractor or DoclingExtractor instance
    """
    # Extract just the filename if full path is provided
    filename = os.path.basename(pdf_filename)

    # Check if PDF requires Docling (has tables/complex structure)
    if filename in config.TABLE_PDFS:
        return DoclingExtractor(text_splitter)
    else:
        return PyMuPDFExtractor()
