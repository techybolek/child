"""
Surgical reload of a single PDF to Qdrant.

Deletes all chunks for a specific PDF and reloads it with the fixed text cleaner.
Avoids expensive full database reload.

Usage:
    python reload_single_pdf.py bcy-26-income-eligibility-and-maximum-psoc-twc.pdf
"""

import os
import sys
import json
import glob
import logging
from typing import List, Dict, Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.docstore.document import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DocItemLabel

import config
from contextual_processor import ContextualChunkProcessor
from prompts import MASTER_CONTEXT
from text_cleaner import clean_text, is_likely_toc, is_markdown_table
from extractors import get_extractor
from shared import (
    clean_documents,
    filter_toc_chunks,
    add_chunk_metadata,
    enrich_metadata,
    upload_with_embeddings
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class SinglePDFReloader:
    """Surgically reload a single PDF to Qdrant."""

    def __init__(self, pdf_filename: str, contextual_mode: bool = True, hybrid_mode: bool = False):
        """
        Initialize the single PDF reloader.

        Args:
            pdf_filename: Name of the PDF file (e.g., 'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf')
            contextual_mode: If True, uses contextual embeddings
            hybrid_mode: If True, uses hybrid embeddings (dense + sparse)
        """
        self.pdf_filename = pdf_filename
        self.contextual_mode = contextual_mode
        self.hybrid_mode = hybrid_mode

        # Use unified collection (hybrid schema supports all modes)
        self.collection_name = config.QDRANT_COLLECTION_NAME
        logger.info(f"Using collection: {self.collection_name}")

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

        # Initialize OpenAI embeddings
        logger.info(f"Initializing OpenAI embeddings: {config.EMBEDDING_MODEL}")
        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY
        )

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=config.CHUNK_SEPARATORS,
            length_function=len,
        )

        # Initialize contextual processor if enabled
        self.contextual_processor = None
        self.document_context = None  # Store document context for upload
        if self.contextual_mode:
            logger.info(f"Initializing contextual processor with model: {config.GROQ_MODEL}")
            self.contextual_processor = ContextualChunkProcessor(
                groq_api_key=config.GROQ_API_KEY,
                model=config.GROQ_MODEL
            )

        # Build metadata index for source_url lookup
        self._metadata_index = self._build_metadata_index()

    def _build_metadata_index(self) -> Dict[str, Dict[str, Any]]:
        """Build index mapping PDF filenames to their metadata from JSON files."""
        index = {}
        json_pattern = os.path.join(config.PDFS_DIR, "*_pdf.json")

        for json_path in glob.glob(json_pattern):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                if 'filename' in data:
                    index[data['filename']] = data
            except Exception as e:
                logger.warning(f"Could not load metadata from {json_path}: {e}")

        logger.info(f"Built metadata index with {len(index)} entries")
        return index

    def load_pdf_metadata(self, pdf_filename: str) -> Optional[Dict[str, Any]]:
        """Load metadata JSON for a PDF by matching the filename field."""
        return self._metadata_index.get(pdf_filename)

    def delete_pdf_chunks(self):
        """Delete all chunks for this PDF from Qdrant."""
        logger.info(f"Deleting all chunks for: {self.pdf_filename}")

        try:
            # Scroll through all points and filter in Python
            # (Qdrant requires index for keyword filtering, simpler to filter locally)
            logger.info("Scrolling through collection to find matching chunks...")

            point_ids = []
            offset = None
            batch_size = 100

            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,  # Need payload to check 'doc' field
                    with_vectors=False
                )

                points, next_offset = result

                if not points:
                    break

                # Filter points that match our PDF
                # Check both 'doc' and 'filename' fields for backward compatibility
                for point in points:
                    if point.payload:
                        doc_value = point.payload.get('doc', '')
                        filename_value = point.payload.get('filename', '')
                        if doc_value == self.pdf_filename or filename_value == self.pdf_filename:
                            point_ids.append(point.id)

                if next_offset is None:
                    break

                offset = next_offset

            if point_ids:
                logger.info(f"Found {len(point_ids)} chunks to delete")
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.info(f"✓ Deleted {len(point_ids)} chunks")
            else:
                logger.warning(f"No chunks found for {self.pdf_filename}")

            return len(point_ids)

        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise

    def process_pdf(self, pdf_path: str) -> List[Document]:
        """
        Process a single PDF file.

        Args:
            pdf_path: Full path to PDF file

        Returns:
            List of Document chunks
        """
        try:
            logger.info(f"Processing: {pdf_path}")

            # Get appropriate extractor and extract PDF content
            extractor = get_extractor(self.pdf_filename, self.text_splitter)

            # Log extractor type
            if self.pdf_filename in config.TABLE_PDFS:
                logger.info(f"✓ PDF in table whitelist, using Docling")
            else:
                logger.info(f"→ Standard PDF, using PyMuPDF")

            pages = extractor.extract(pdf_path)

            # Determine total pages for metadata
            is_docling = pages and pages[0].metadata.get('extractor') == 'docling'
            if is_docling:
                # For Docling, count unique pages in metadata
                unique_pages = set(doc.metadata.get('page', 0) for doc in pages)
                total_pages = len(unique_pages)
            else:
                # For PyMuPDF, len(pages) = pages since it's 1 doc per page
                total_pages = len(pages)

            logger.info(f"Loaded {total_pages} pages")

            # Clean page content
            pages = clean_documents(pages)

            # Load metadata from JSON file if available
            metadata_json = self.load_pdf_metadata(self.pdf_filename)
            if metadata_json:
                logger.info(f"Found metadata: source_url={metadata_json.get('source_url', 'N/A')}")

            # Enrich metadata to match bulk loader format
            pages = enrich_metadata(pages, self.pdf_filename, metadata_json, total_pages)

            # Split into chunks
            # Docling PDFs are already chunked at item level
            # PyMuPDF PDFs need chunking
            if is_docling:
                # Docling already returned item-level chunks, use as-is
                chunks = pages
                table_chunks = sum(1 for d in pages if d.metadata.get('chunk_type') == 'table')
                narrative_chunks = sum(1 for d in pages if d.metadata.get('chunk_type') == 'narrative')
                logger.info(f"Docling PDF: {total_pages} pages → {len(chunks)} chunks ({table_chunks} tables, {narrative_chunks} narrative)")
            elif len(pages) == 1:
                chunks = pages  # Don't split, use entire page as one chunk
                page_chars = len(pages[0].page_content)
                logger.info(f"Single-page PDF: loading as 1 chunk ({page_chars} characters)")
            else:
                chunks = self.text_splitter.split_documents(pages)
                logger.info(f"Multi-page PDF ({len(pages)} pages): split into {len(chunks)} chunks")

            # Filter out TOC chunks
            original_count = len(chunks)
            chunks, filtered_count = filter_toc_chunks(chunks)

            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} TOC chunks ({filtered_count/original_count*100:.1f}%)")

            logger.info(f"Created {len(chunks)} chunks after filtering")

            # Add chunk index to metadata (re-index after filtering)
            chunks = add_chunk_metadata(chunks)

            # Generate document context if in contextual mode (will be used during upload)
            if self.contextual_mode and self.contextual_processor:
                logger.info("Generating document context...")

                # Generate document context
                full_text = "\n\n".join([page.page_content for page in pages])
                pdf_id = self.pdf_filename
                document_title = self.pdf_filename.replace('.pdf', '').replace('-', ' ').title()
                first_2000_chars = full_text[:2000]

                self.document_context = self.contextual_processor.generate_document_context(
                    pdf_id=pdf_id,
                    document_title=document_title,
                    total_pages=len(pages),
                    first_2000_chars=first_2000_chars
                )

                if self.document_context:
                    logger.info("✓ Document context generated")
                else:
                    logger.warning("Failed to generate document context")
                    self.document_context = None

            return chunks

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise

    def upload_chunks(self, chunks: List[Document]):
        """Upload chunks to Qdrant."""
        if not chunks:
            logger.warning("No chunks to upload")
            return

        # Use shared upload function
        upload_with_embeddings(
            client=self.client,
            collection_name=self.collection_name,
            documents=chunks,
            embeddings_model=self.embeddings,
            contextual_mode=self.contextual_mode,
            contextual_processor=self.contextual_processor,
            document_context=self.document_context,
            hybrid_mode=self.hybrid_mode
        )

    def reload(self, pdf_path: str):
        """
        Full surgical reload: delete old chunks and upload new ones.

        Args:
            pdf_path: Full path to PDF file
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"SURGICAL RELOAD: {self.pdf_filename}")
        logger.info(f"{'='*60}\n")

        # Step 1: Delete old chunks
        deleted_count = self.delete_pdf_chunks()

        # Step 2: Process PDF with FIXED text cleaner
        chunks = self.process_pdf(pdf_path)

        # Step 3: Upload new chunks
        self.upload_chunks(chunks)

        logger.info(f"\n{'='*60}")
        logger.info(f"RELOAD COMPLETE")
        logger.info(f"Deleted: {deleted_count} old chunks")
        logger.info(f"Uploaded: {len(chunks)} new chunks")
        logger.info(f"{'='*60}\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Surgically reload a single PDF to Qdrant')
    parser.add_argument('pdf_filename', help='PDF filename (e.g., bcy-26-income-eligibility-and-maximum-psoc-twc.pdf)')
    parser.add_argument('--contextual', action='store_true', dest='contextual',
                       help='Enable contextual retrieval mode (override config default)')
    parser.add_argument('--no-contextual', action='store_true', dest='no_contextual',
                       help='Disable contextual retrieval mode (override config default)')
    parser.add_argument('--hybrid', action='store_true', dest='hybrid',
                       help='Enable hybrid search mode (override config default)')
    parser.add_argument('--no-hybrid', action='store_true', dest='no_hybrid',
                       help='Disable hybrid search mode (override config default)')

    args = parser.parse_args()

    # Apply precedence: explicit disable > explicit enable > config default
    # Contextual mode
    if args.no_contextual:
        contextual_mode = False
    elif args.contextual:
        contextual_mode = True
    else:
        contextual_mode = config.ENABLE_CONTEXTUAL_RETRIEVAL

    # Hybrid mode
    if args.no_hybrid:
        hybrid_mode = False
    elif args.hybrid:
        hybrid_mode = True
    else:
        hybrid_mode = True  # Default to hybrid since collection uses hybrid schema

    # Find the PDF file
    pdf_dir = config.PDFS_DIR
    pdf_path = os.path.join(pdf_dir, args.pdf_filename)

    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found: {pdf_path}")
        sys.exit(1)

    logger.info(f"Found PDF: {pdf_path}")

    # Create reloader and execute
    reloader = SinglePDFReloader(
        pdf_filename=args.pdf_filename,
        contextual_mode=contextual_mode,
        hybrid_mode=hybrid_mode
    )
    reloader.reload(pdf_path)

    logger.info("✓ Surgical reload complete!")


if __name__ == '__main__':
    main()
