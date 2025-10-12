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

# Add parent directory to path to import SCRAPER module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain.docstore.document import Document
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

from SCRAPER import config

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

    def __init__(self, test_mode: bool = False, max_pdfs: Optional[int] = None, clear_collection: bool = True):
        """
        Initialize the PDF to Qdrant loader.

        Args:
            test_mode: If True, runs in test mode with limited PDFs
            max_pdfs: Maximum number of PDFs to process (for testing)
            clear_collection: If True, clears the collection before loading (default: True)
        """
        self.test_mode = test_mode
        self.max_pdfs = max_pdfs or (3 if test_mode else None)
        self.clear_collection = clear_collection

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

        # Statistics
        self.stats = {
            'pdfs_processed': 0,
            'pdfs_failed': 0,
            'total_chunks': 0,
            'total_pages': 0,
            'start_time': datetime.now(),
            'failed_pdfs': []
        }

    def clear_and_recreate_collection(self):
        """Delete and recreate the Qdrant collection (clears all data)."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            # Delete existing collection if it exists
            if config.QDRANT_COLLECTION_NAME in collection_names:
                logger.warning(f"Deleting existing collection '{config.QDRANT_COLLECTION_NAME}'")
                self.client.delete_collection(config.QDRANT_COLLECTION_NAME)
                logger.info("Collection deleted successfully")

            # Create fresh collection
            logger.info(f"Creating fresh collection '{config.QDRANT_COLLECTION_NAME}'")
            self.client.create_collection(
                collection_name=config.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=config.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            logger.info("Collection created successfully")
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            raise

    def ensure_collection_exists(self):
        """Ensure the Qdrant collection exists, create if not."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if config.QDRANT_COLLECTION_NAME in collection_names:
                logger.info(f"Collection '{config.QDRANT_COLLECTION_NAME}' already exists")
                # Get collection info
                collection_info = self.client.get_collection(config.QDRANT_COLLECTION_NAME)
                logger.info(f"Current vectors count: {collection_info.points_count}")
            else:
                logger.info(f"Creating collection '{config.QDRANT_COLLECTION_NAME}'")
                self.client.create_collection(
                    collection_name=config.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=config.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Collection created successfully")
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
        chunked_docs = self.text_splitter.split_documents(documents)

        # Add chunk index to metadata
        for i, doc in enumerate(chunked_docs):
            doc.metadata['chunk_index'] = i
            doc.metadata['total_chunks'] = len(chunked_docs)

        logger.info(f"Created {len(chunked_docs)} chunks from {os.path.basename(pdf_path)}")
        self.stats['total_chunks'] += len(chunked_docs)

        return chunked_docs

    def upload_documents_to_qdrant(self, documents: List[Document]):
        """
        Upload documents to Qdrant with embeddings.

        Args:
            documents: List of LangChain Document objects
        """
        if not documents:
            return

        logger.info(f"Generating embeddings for {len(documents)} chunks...")

        # Generate embeddings
        texts = [doc.page_content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)

        # Get current max ID to avoid conflicts
        try:
            collection_info = self.client.get_collection(config.QDRANT_COLLECTION_NAME)
            current_count = collection_info.points_count
        except:
            current_count = 0

        # Create points
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            point_id = current_count + i + 1

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
                collection_name=config.QDRANT_COLLECTION_NAME,
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

Collection: {config.QDRANT_COLLECTION_NAME}
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

    args = parser.parse_args()

    loader = PDFToQdrantLoader(
        test_mode=args.test,
        max_pdfs=args.max_pdfs,
        clear_collection=not args.no_clear  # Clear by default, unless --no-clear is specified
    )

    loader.run()


if __name__ == '__main__':
    main()
