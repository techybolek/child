"""
PyMuPDF PDF extractor for standard text extraction.
"""

from typing import List
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.docstore.document import Document


class PyMuPDFExtractor:
    """Extract PDF content using PyMuPDF (fast, standard text extraction)."""

    def extract(self, pdf_path: str) -> List[Document]:
        """
        Extract PDF content using PyMuPDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of LangChain Document objects (one per page)
        """
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()
        return documents
