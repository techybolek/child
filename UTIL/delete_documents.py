"""
Delete specific PDF documents from Qdrant collection.

Surgically removes chunks for specified PDFs without reloading the entire collection.

Usage:
    python delete_documents.py
"""

import os
import logging
from typing import List
from qdrant_client import QdrantClient
import config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# Documents to remove (2024 and 2025 versions)
DOCUMENTS_TO_DELETE = [
    # 2024 Documents
    'wd-24-23-att1-twc.pdf',
    'acf-218-qpr-ffy-2024-for-texas.pdf',
    'texas-early-learning-strategic-plan-2024-2026-final-accessible.pdf',

    # 2025 Documents
    'bcy2025-psoc-chart-twc.pdf',
    'bcy25-board-max-provider-payment-rates-4-age-groups-twc.pdf',
    'bcy25-child-care-provider-payment-rates-twc.pdf',
    'tx-ccdf-state-plan-ffy2025-2027-approved.pdf',
]


class DocumentDeleter:
    """Delete specific documents from Qdrant collection."""

    def __init__(self, collection_name: str = None):
        """
        Initialize the document deleter.

        Args:
            collection_name: Qdrant collection name (default: contextual collection)
        """
        self.collection_name = collection_name or config.QDRANT_COLLECTION_NAME_CONTEXTUAL
        logger.info(f"Using collection: {self.collection_name}")

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

    def delete_documents(self, document_names: List[str]) -> dict:
        """
        Delete all chunks for specified documents from Qdrant.

        Args:
            document_names: List of PDF filenames to delete

        Returns:
            Dictionary with deletion statistics
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"DELETING {len(document_names)} DOCUMENTS")
        logger.info(f"{'='*60}\n")

        total_deleted = 0
        deletion_stats = {}

        for pdf_filename in document_names:
            logger.info(f"Processing: {pdf_filename}")

            try:
                # Scroll through all points and filter in Python
                logger.info("  Searching for matching chunks...")

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
                    for point in points:
                        if point.payload and point.payload.get('filename') == pdf_filename:
                            point_ids.append(point.id)

                    if next_offset is None:
                        break

                    offset = next_offset

                if point_ids:
                    logger.info(f"  Found {len(point_ids)} chunks to delete")
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=point_ids
                    )
                    logger.info(f"  ✓ Deleted {len(point_ids)} chunks")
                    deletion_stats[pdf_filename] = len(point_ids)
                    total_deleted += len(point_ids)
                else:
                    logger.warning(f"  ⚠ No chunks found for {pdf_filename}")
                    deletion_stats[pdf_filename] = 0

            except Exception as e:
                logger.error(f"  ✗ Error deleting {pdf_filename}: {e}")
                deletion_stats[pdf_filename] = -1

        logger.info(f"\n{'='*60}")
        logger.info(f"DELETION COMPLETE")
        logger.info(f"Total documents processed: {len(document_names)}")
        logger.info(f"Total chunks deleted: {total_deleted}")
        logger.info(f"{'='*60}\n")

        return {
            'total_documents': len(document_names),
            'total_chunks_deleted': total_deleted,
            'per_document': deletion_stats
        }


def main():
    """Main entry point."""
    logger.info(f"Documents to delete: {len(DOCUMENTS_TO_DELETE)}")
    for doc in DOCUMENTS_TO_DELETE:
        logger.info(f"  - {doc}")

    # Confirm before proceeding
    print("\n⚠️  WARNING: This will permanently delete the above documents from Qdrant.")
    response = input("Continue? (yes/no): ")

    if response.lower() != 'yes':
        logger.info("Deletion cancelled.")
        return

    # Create deleter and execute
    deleter = DocumentDeleter()
    stats = deleter.delete_documents(DOCUMENTS_TO_DELETE)

    # Print summary
    logger.info("\nDeletion Summary:")
    for doc, count in stats['per_document'].items():
        if count == -1:
            logger.error(f"  ✗ {doc}: ERROR")
        elif count == 0:
            logger.warning(f"  ⚠ {doc}: 0 chunks (not found)")
        else:
            logger.info(f"  ✓ {doc}: {count} chunks deleted")

    logger.info(f"\n✓ Total: {stats['total_chunks_deleted']} chunks deleted from {stats['total_documents']} documents")


if __name__ == '__main__':
    main()
