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
    from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

import config
from contextual_processor import ContextualChunkProcessor
from prompts import MASTER_CONTEXT
from text_cleaner import clean_text, is_likely_toc


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
            contextual_mode: If True, generates contextual metadata for chunks
        """
        self.test_mode = test_mode
        self.max_pdfs = max_pdfs or (3 if test_mode else None)
        self.clear_collection = clear_collection
        self.contextual_mode = contextual_mode

        # Set collection name based on contextual mode
        self.collection_name = config.QDRANT_COLLECTION_NAME_CONTEXTUAL if contextual_mode else config.QDRANT_COLLECTION_NAME

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
            'contextual_mode': self.contextual_mode
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

            # Create fresh collection
            logger.info(f"Creating fresh collection '{self.collection_name}'")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=config.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
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
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=config.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
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
        Process a single PDF: load with LangChain, chunk, and prepare documents.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of LangChain Document objects
        """
        logger.info(f"Processing PDF: {os.path.basename(pdf_path)}")

        # Load PDF using LangChain's PyMuPDFLoader
        # This automatically extracts text and creates Document objects with page metadata
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()

        if not documents:
            logger.warning(f"No content extracted from {pdf_path}")
            return []

        # Update stats
        self.stats['total_pages'] += len(documents)
        logger.info(f"Loaded {len(documents)} pages from {os.path.basename(pdf_path)}")

        # Clean page numbers and artifacts from extracted text
        for doc in documents:
            doc.page_content = clean_text(doc.page_content)

        # Load metadata from JSON file if available
        metadata_json = self.load_pdf_metadata(pdf_path)

        # Enrich metadata for all documents
        for doc in documents:
            # Add filename and content type
            doc.metadata['filename'] = os.path.basename(pdf_path)
            doc.metadata['content_type'] = 'pdf'

            # Add metadata from JSON if available
            if metadata_json:
                doc.metadata.update({
                    'source_url': metadata_json.get('source_url', ''),
                    'pdf_id': metadata_json.get('pdf_id', ''),
                    'file_size_mb': metadata_json.get('file_size_mb', 0),
                    'total_pages': metadata_json.get('page_count', len(documents))
                })

        # Split documents into chunks
        # Special case: Single-page PDFs are loaded as a single chunk to preserve table structure
        if len(documents) == 1:
            chunked_docs = documents  # Don't split, use entire page as one chunk
            page_chars = len(documents[0].page_content)
            logger.info(f"  Single-page PDF: loading as 1 chunk ({page_chars} characters)")
        else:
            chunked_docs = self.text_splitter.split_documents(documents)
            logger.info(f"  Multi-page PDF ({len(documents)} pages): split into {len(chunked_docs)} chunks")

        original_chunk_count = len(chunked_docs)

        # Filter out table of contents and structural metadata chunks
        filtered_chunks = []
        toc_chunks_filtered = 0
        for doc in chunked_docs:
            if not is_likely_toc(doc.page_content):
                filtered_chunks.append(doc)
            else:
                toc_chunks_filtered += 1
                logger.debug(f"Filtered out TOC chunk: {doc.page_content[:100]}...")
                # Track filtered chunk for reporting
                self.filtered_chunks.append({
                    'pdf_name': os.path.basename(pdf_path),
                    'chunk_preview': doc.page_content[:200],
                    'chunk_length': len(doc.page_content)
                })

        chunked_docs = filtered_chunks
        if toc_chunks_filtered > 0:
            logger.info(f"Filtered out {toc_chunks_filtered} TOC/metadata chunks ({original_chunk_count} → {len(chunked_docs)})")

        self.stats['total_filtered_chunks'] += toc_chunks_filtered

        # Add chunk index to metadata (re-index after filtering)
        for i, doc in enumerate(chunked_docs):
            doc.metadata['chunk_index'] = i
            doc.metadata['total_chunks'] = len(chunked_docs)

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

        logger.info(f"Generating embeddings for {len(documents)} chunks...")

        # Store original content before any modifications
        original_contents = [doc.page_content for doc in documents]
        
        # Prepare content for embedding (may include context)
        texts_for_embedding = []

        # Generate contextual metadata if in contextual mode
        if self.contextual_mode and self.contextual_processor and documents:
            logger.info("Generating contextual metadata for chunks...")

            # Get pdf_id from first document metadata
            pdf_id = documents[0].metadata.get('pdf_id', documents[0].metadata.get('filename', ''))
            if pdf_id.endswith('.pdf'):
                pdf_id = os.path.splitext(pdf_id)[0]

            # Get document context from cache
            document_context = self.document_context_cache.get(pdf_id)

            if document_context:
                # Prepare chunk data for context generation
                chunks_for_context = []
                for doc in documents:
                    chunks_for_context.append({
                        'page_num': doc.metadata.get('page', 1),
                        'total_pages': doc.metadata.get('total_pages', 1),
                        'chunk_index': doc.metadata.get('chunk_index', 0),
                        'total_chunks': doc.metadata.get('total_chunks', 1),
                        'chunk_text': doc.page_content,
                    })

                # Generate chunk contexts in batches
                chunk_contexts = self.contextual_processor.generate_all_chunk_contexts(
                    chunks_for_context,
                    document_context
                )

                # Prepare enriched text for embedding and store contexts in metadata
                for i, doc in enumerate(documents):
                    # Store all contexts in metadata (for retrieval visibility and future use)
                    doc.metadata['master_context'] = MASTER_CONTEXT
                    doc.metadata['document_context'] = document_context
                    doc.metadata['has_context'] = True

                    if chunk_contexts and i in chunk_contexts:
                        chunk_context = chunk_contexts[i]
                        doc.metadata['chunk_context'] = chunk_context
                    else:
                        doc.metadata['chunk_context'] = None

                    # Build enriched text for embedding ONLY
                    # This improves embedding relevance but isn't stored in page_content
                    enriched_for_embedding = f"{MASTER_CONTEXT}\n\n{document_context}"
                    if doc.metadata.get('chunk_context'):
                        enriched_for_embedding += f"\n\n{doc.metadata['chunk_context']}"
                    enriched_for_embedding += f"\n\n{original_contents[i]}"
                    
                    texts_for_embedding.append(enriched_for_embedding)

                logger.info(f"Generated contexts for {len(documents)} chunks")
                logger.info("Using enriched context for embeddings, but storing only original content")
            else:
                logger.warning(f"No document context available for {pdf_id}, using original content only")
                for doc in documents:
                    doc.metadata['has_context'] = False
                texts_for_embedding = original_contents.copy()
        else:
            # Non-contextual mode: use original content as-is
            for doc in documents:
                doc.metadata['has_context'] = False
            texts_for_embedding = original_contents.copy()

        # Generate embeddings from potentially enriched text
        embeddings = self.embeddings.embed_documents(texts_for_embedding)

        # Get current max ID to avoid conflicts
        try:
            collection_info = self.client.get_collection(self.collection_name)
            current_count = collection_info.points_count
        except:
            current_count = 0

        # Create points (always use original content in page_content, not enriched)
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            point_id = current_count + i + 1

            # Ensure page_content is original (not enriched with contexts)
            doc.page_content = original_contents[i]

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    'text': doc.page_content,
                    **doc.metadata
                }
            )
            points.append(point)

        # Upload in batches
        batch_size = config.UPLOAD_BATCH_SIZE
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            logger.info(f"Uploaded batch {i//batch_size + 1} ({len(batch)} points)")

        logger.info(f"Successfully uploaded {len(documents)} chunks to Qdrant")

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
    parser.add_argument('--contextual', action='store_true',
                       help='Enable contextual retrieval mode (generates 3-tier context hierarchy)')

    args = parser.parse_args()

    loader = PDFToQdrantLoader(
        test_mode=args.test,
        max_pdfs=args.max_pdfs,
        clear_collection=not args.no_clear,  # Clear by default, unless --no-clear is specified
        contextual_mode=args.contextual
    )

    loader.run()


if __name__ == '__main__':
    main()
