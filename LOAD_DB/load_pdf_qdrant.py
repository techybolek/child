"""
Load PDFs to Qdrant Vector Database
Extracts text from PDFs, chunks them, generates embeddings, and uploads to Qdrant
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import glob

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain.docstore.document import Document
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType, SparseVectorParams
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DocItemLabel
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

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


def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        config.LOAD_DB_LOGS_DIR,
        config.LOAD_DB_CHECKPOINTS_DIR,
        config.LOAD_DB_REPORTS_DIR,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Ensure directories exist before logging setup
ensure_directories()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(config.LOAD_DB_LOGS_DIR, f'pdf_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFToQdrantLoader:
    """Handles loading PDFs to Qdrant vector database."""

    def __init__(self, test_mode: bool = False, max_pdfs: Optional[int] = None, clear_collection: bool = True, contextual_mode: bool = False):
        """
        Initialize the PDF to Qdrant loader.

        Args:
            test_mode: If True, runs in test mode with limited PDFs
            max_pdfs: Maximum number of PDFs to process (for testing)
            clear_collection: If True, clears the collection before loading (default: True)
            contextual_mode: If True, generates contextual metadata for chunks (improves dense embeddings)
        """
        self.test_mode = test_mode
        self.max_pdfs = max_pdfs or (3 if test_mode else None)
        self.clear_collection = clear_collection
        self.contextual_mode = contextual_mode

        # Single unified collection with hybrid schema (dense + sparse vectors)
        self.collection_name = config.QDRANT_COLLECTION_NAME

        # Initialize Qdrant client
        if not config.QDRANT_API_URL or not config.QDRANT_API_KEY:
            raise ValueError("QDRANT_API_URL and QDRANT_API_KEY must be set in environment")

        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

        # Initialize OpenAI embeddings
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in environment")

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
        self.document_context_cache = {}
        if self.contextual_mode:
            if not config.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY must be set in environment for contextual mode")
            logger.info(f"Initializing contextual processor with model: {config.GROQ_MODEL}")
            self.contextual_processor = ContextualChunkProcessor(
                groq_api_key=config.GROQ_API_KEY,
                model=config.GROQ_MODEL
            )
            logger.info("Contextual processor initialized")

        # Statistics
        self.stats = {
            'pdfs_processed': 0,
            'pdfs_failed': 0,
            'total_chunks': 0,
            'total_pages': 0,
            'total_filtered_chunks': 0,
            'start_time': datetime.now(),
            'failed_pdfs': [],
            'contextual_mode': self.contextual_mode,
            'tables_detected': 0,
            'docling_used': 0,
            'pymupdf_used': 0
        }

        # Track filtered chunks for reporting
        self.filtered_chunks = []

    def clear_and_recreate_collection(self):
        """Delete and recreate the Qdrant collection (clears all data)."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            # Delete existing collection if it exists
            if self.collection_name in collection_names:
                logger.warning(f"Deleting existing collection '{self.collection_name}'")
                self.client.delete_collection(self.collection_name)
                logger.info("Collection deleted successfully")

            # Create fresh collection with hybrid schema (always)
            logger.info(f"Creating fresh collection '{self.collection_name}'")
            logger.info("Creating collection with dense + sparse vectors (hybrid schema)")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=config.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams()
                }
            )
            logger.info("Collection created successfully")

            # Create payload index on filename field for efficient filtering
            logger.info("Creating payload index on 'filename' field")
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name='filename',
                field_schema=PayloadSchemaType.KEYWORD
            )
            logger.info("Payload index created successfully")
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            raise

    def ensure_collection_exists(self):
        """Ensure the Qdrant collection exists, create if not."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                # Get collection info
                collection_info = self.client.get_collection(self.collection_name)
                logger.info(f"Current vectors count: {collection_info.points_count}")
            else:
                logger.info(f"Creating collection '{self.collection_name}'")
                logger.info("Creating collection with dense + sparse vectors (hybrid schema)")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=config.EMBEDDING_DIMENSION,
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams()
                    }
                )
                logger.info("Collection created successfully")

                # Create payload index on filename field for efficient filtering
                logger.info("Creating payload index on 'filename' field")
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name='filename',
                    field_schema=PayloadSchemaType.KEYWORD
                )
                logger.info("Payload index created successfully")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    def load_pdf_metadata(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Load metadata JSON for a PDF if it exists."""
        pdf_name = os.path.basename(pdf_path)
        pdf_id = os.path.splitext(pdf_name)[0]

        # Try to find matching metadata JSON
        metadata_patterns = [
            os.path.join(config.PDFS_DIR, f"{pdf_id}_pdf.json"),
            os.path.join(config.PDFS_DIR, pdf_id + ".json")
        ]

        for metadata_path in metadata_patterns:
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load metadata from {metadata_path}: {e}")

        return None

    def process_pdf(self, pdf_path: str) -> List[Document]:
        """
        Process a single PDF: check config for table PDFs, route to appropriate extraction method, chunk, and prepare documents.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Processing PDF: {os.path.basename(pdf_path)}")

        # Get appropriate extractor and extract PDF content
        pdf_filename = os.path.basename(pdf_path)
        extractor = get_extractor(pdf_filename, self.text_splitter)

        # Log extractor type and update stats
        if pdf_filename in config.TABLE_PDFS:
            logger.info(f"  ✓ PDF in table whitelist, using Docling")
            self.stats['tables_detected'] += 1
            self.stats['docling_used'] += 1
        else:
            logger.info(f"  → Standard PDF, using PyMuPDF")
            self.stats['pymupdf_used'] += 1

        documents = extractor.extract(pdf_path)

        if not documents:
            logger.warning(f"No content extracted from {pdf_path}")
            return []

        # Clean page numbers and artifacts from extracted text
        documents = clean_documents(documents)

        # Load metadata from JSON file if available
        metadata_json = self.load_pdf_metadata(pdf_path)

        # Determine total pages for metadata
        is_docling = documents and documents[0].metadata.get('extractor') == 'docling'
        if is_docling:
            # For Docling, count unique pages in metadata
            unique_pages = set(doc.metadata.get('page', 0) for doc in documents)
            total_pages = len(unique_pages)
        else:
            # For PyMuPDF, len(documents) = pages since it's 1 doc per page
            total_pages = len(documents)

        self.stats['total_pages'] += total_pages
        logger.info(f"Loaded {total_pages} pages from {os.path.basename(pdf_path)}")

        # Enrich metadata for all documents
        documents = enrich_metadata(documents, pdf_filename, metadata_json, total_pages)

        # Split documents into chunks
        # Docling PDFs are already chunked at item level
        # PyMuPDF PDFs need chunking
        if is_docling:
            # Docling already returned item-level chunks, use as-is
            chunked_docs = documents
            table_chunks = sum(1 for d in documents if d.metadata.get('chunk_type') == 'table')
            narrative_chunks = sum(1 for d in documents if d.metadata.get('chunk_type') == 'narrative')
            logger.info(f"  Docling PDF: {total_pages} pages → {len(chunked_docs)} chunks ({table_chunks} tables, {narrative_chunks} narrative)")
        elif len(documents) == 1:
            chunked_docs = documents  # Don't split, use entire page as one chunk
            page_chars = len(documents[0].page_content)
            logger.info(f"  Single-page PDF: loading as 1 chunk ({page_chars} characters)")
        else:
            chunked_docs = self.text_splitter.split_documents(documents)
            logger.info(f"  Multi-page PDF ({len(documents)} pages): split into {len(chunked_docs)} chunks")

        original_chunk_count = len(chunked_docs)

        # Filter out table of contents and structural metadata chunks
        chunked_docs, toc_chunks_filtered = filter_toc_chunks(chunked_docs)

        # Track filtered chunks for reporting
        if toc_chunks_filtered > 0:
            logger.info(f"Filtered out {toc_chunks_filtered} TOC/metadata chunks ({original_chunk_count} → {len(chunked_docs)})")
            # Note: Detailed tracking of filtered chunks removed for simplicity
            # Could be re-added to filter_toc_chunks if needed

        self.stats['total_filtered_chunks'] += toc_chunks_filtered

        # Add chunk index to metadata (re-index after filtering)
        chunked_docs = add_chunk_metadata(chunked_docs)

        logger.info(f"Created {len(chunked_docs)} chunks from {os.path.basename(pdf_path)}")
        self.stats['total_chunks'] += len(chunked_docs)

        # Generate document context if in contextual mode
        if self.contextual_mode and self.contextual_processor:
            pdf_name = os.path.basename(pdf_path)
            pdf_id = os.path.splitext(pdf_name)[0]

            # Get first 2000 chars from combined document content
            combined_content = "\n".join([doc.page_content for doc in documents])
            first_2000_chars = combined_content[:2000]

            # Get document metadata for context generation
            document_title = pdf_name
            total_pages = len(documents)

            document_context = self.contextual_processor.generate_document_context(
                pdf_id=pdf_id,
                document_title=document_title,
                total_pages=total_pages,
                first_2000_chars=first_2000_chars,
            )

            if document_context:
                self.document_context_cache[pdf_id] = document_context
                logger.info(f"Generated document context for {pdf_id}")
            else:
                logger.warning(f"Failed to generate document context for {pdf_id}")
                self.document_context_cache[pdf_id] = None

        return chunked_docs

    def upload_documents_to_qdrant(self, documents: List[Document]):
        """
        Upload documents to Qdrant with embeddings.

        For contextual mode:
        - Embedding is computed from [Master + Document + Chunk contexts + Original content]
        - Storage keeps only original content in page_content
        - Contexts stored separately in metadata for potential future use

        Args:
            documents: List of LangChain Document objects
        """
        if not documents:
            return

        # Get document context from cache if in contextual mode
        document_context = None
        if self.contextual_mode and documents:
            pdf_id = documents[0].metadata.get('pdf_id', documents[0].metadata.get('filename', ''))
            if pdf_id.endswith('.pdf'):
                pdf_id = os.path.splitext(pdf_id)[0]
            document_context = self.document_context_cache.get(pdf_id)

        # Use shared upload function (always hybrid schema)
        upload_with_embeddings(
            client=self.client,
            collection_name=self.collection_name,
            documents=documents,
            embeddings_model=self.embeddings,
            contextual_mode=self.contextual_mode,
            contextual_processor=self.contextual_processor,
            document_context=document_context,
            hybrid_mode=True  # Always generate sparse vectors for hybrid schema
        )

    def get_pdf_files(self) -> List[str]:
        """Get list of PDF files to process."""
        pdf_pattern = os.path.join(config.PDFS_DIR, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)

        if self.max_pdfs:
            pdf_files = pdf_files[:self.max_pdfs]

        logger.info(f"Found {len(pdf_files)} PDF files to process")
        return pdf_files

    def save_checkpoint(self, processed_pdfs: List[str]):
        """Save processing checkpoint."""
        checkpoint_path = os.path.join(
            config.LOAD_DB_CHECKPOINTS_DIR,
            f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        checkpoint_data = {
            'processed_pdfs': processed_pdfs,
            'stats': {
                **self.stats,
                'start_time': self.stats['start_time'].isoformat(),
                'checkpoint_time': datetime.now().isoformat()
            }
        }

        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        logger.info(f"Checkpoint saved to {checkpoint_path}")

    def write_filtered_chunks_report(self):
        """Write detailed log of all filtered chunks to a dedicated file."""
        if not self.filtered_chunks:
            logger.info("No chunks were filtered out.")
            return

        filtered_report_path = os.path.join(
            config.LOAD_DB_REPORTS_DIR,
            f"filtered_chunks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(filtered_report_path, 'w') as f:
            f.write("FILTERED CHUNKS REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total chunks filtered: {self.stats['total_filtered_chunks']}\n")
            f.write(f"Total filtered entries: {len(self.filtered_chunks)}\n")
            f.write("\n" + "=" * 80 + "\n\n")

            # Group by PDF for better readability
            by_pdf = {}
            for chunk in self.filtered_chunks:
                pdf_name = chunk['pdf_name']
                if pdf_name not in by_pdf:
                    by_pdf[pdf_name] = []
                by_pdf[pdf_name].append(chunk)

            for pdf_name in sorted(by_pdf.keys()):
                chunks = by_pdf[pdf_name]
                f.write(f"PDF: {pdf_name}\n")
                f.write(f"  Filtered chunks: {len(chunks)}\n")
                f.write("-" * 80 + "\n")

                for i, chunk in enumerate(chunks, 1):
                    f.write(f"\n  Chunk {i} ({chunk['chunk_length']} chars):\n")
                    f.write(f"    {chunk['chunk_preview']}\n")
                    if len(chunk['chunk_preview']) == 200:
                        f.write(f"    [...truncated...]\n")

                f.write("\n" + "=" * 80 + "\n")

        logger.info(f"Filtered chunks report saved to {filtered_report_path}")

    def generate_report(self):
        """Generate final processing report."""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']

        report = f"""
PDF to Qdrant Loading Report
{'=' * 60}

Processing Summary:
  - Total PDFs processed: {self.stats['pdfs_processed']}
  - Total PDFs failed: {self.stats['pdfs_failed']}
  - Total pages extracted: {self.stats['total_pages']}
  - Total chunks created: {self.stats['total_chunks']}
  - Contextual Mode: {self.stats['contextual_mode']}

Table Detection (Two-Tier System):
  - Tables detected: {self.stats['tables_detected']}
  - PDFs processed with Docling: {self.stats['docling_used']}
  - PDFs processed with PyMuPDF: {self.stats['pymupdf_used']}

Collection: {self.collection_name}
  - Qdrant URL: {config.QDRANT_API_URL}
  - Embedding Model: {config.EMBEDDING_MODEL}
  - Chunk Size: {config.CHUNK_SIZE} characters
  - Chunk Overlap: {config.CHUNK_OVERLAP} characters

Timing:
  - Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
  - End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
  - Duration: {duration}

"""

        if self.stats['failed_pdfs']:
            report += f"\nFailed PDFs:\n"
            for pdf in self.stats['failed_pdfs']:
                report += f"  - {pdf}\n"

        report += "\n" + "=" * 60 + "\n"

        # Save report
        report_path = os.path.join(
            config.LOAD_DB_REPORTS_DIR,
            f"load_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(report_path, 'w') as f:
            f.write(report)

        logger.info(f"Report saved to {report_path}")
        print(report)

    def run(self):
        """Main execution method."""
        logger.info("Starting PDF to Qdrant loading process")
        logger.info(f"Test mode: {self.test_mode}")
        logger.info(f"Clear collection: {self.clear_collection}")

        # Clear and recreate collection if requested, otherwise just ensure it exists
        if self.clear_collection:
            self.clear_and_recreate_collection()
        else:
            self.ensure_collection_exists()

        # Get PDF files
        pdf_files = self.get_pdf_files()

        if not pdf_files:
            logger.warning("No PDF files found to process")
            return

        processed_pdfs = []

        # Process each PDF
        for i, pdf_path in enumerate(pdf_files, 1):
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Processing PDF {i}/{len(pdf_files)}: {os.path.basename(pdf_path)}")
                logger.info(f"{'=' * 60}")

                # Process PDF
                documents = self.process_pdf(pdf_path)

                # Upload to Qdrant
                self.upload_documents_to_qdrant(documents)

                self.stats['pdfs_processed'] += 1
                processed_pdfs.append(pdf_path)

                # Save checkpoint every 5 PDFs
                if i % 5 == 0:
                    self.save_checkpoint(processed_pdfs)

            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}", exc_info=True)
                self.stats['pdfs_failed'] += 1
                self.stats['failed_pdfs'].append(os.path.basename(pdf_path))

        # Final checkpoint
        self.save_checkpoint(processed_pdfs)

        # Write filtered chunks report
        self.write_filtered_chunks_report()

        # Generate report
        self.generate_report()

        logger.info("\nPDF loading complete!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Load PDFs to Qdrant Vector Database')
    parser.add_argument('--test', action='store_true', help='Run in test mode (process only 3 PDFs)')
    parser.add_argument('--max-pdfs', type=int, help='Maximum number of PDFs to process')
    parser.add_argument('--no-clear', action='store_true',
                       help='Do NOT clear collection before loading (default: clears collection)')
    parser.add_argument('--contextual', action='store_true', dest='contextual',
                       help='Enable contextual retrieval mode (generates 3-tier context hierarchy for dense embeddings)')
    parser.add_argument('--no-contextual', action='store_true', dest='no_contextual',
                       help='Disable contextual retrieval mode (override config default)')

    args = parser.parse_args()

    # Apply precedence: explicit disable > explicit enable > config default
    if args.no_contextual:
        contextual_mode = False
    elif args.contextual:
        contextual_mode = True
    else:
        contextual_mode = config.ENABLE_CONTEXTUAL_RETRIEVAL

    # Note: Hybrid schema is always used (dense + sparse vectors)
    # Contextual mode only affects dense embedding quality

    loader = PDFToQdrantLoader(
        test_mode=args.test,
        max_pdfs=args.max_pdfs,
        clear_collection=not args.no_clear,  # Clear by default, unless --no-clear is specified
        contextual_mode=contextual_mode
    )

    loader.run()


if __name__ == '__main__':
    main()
