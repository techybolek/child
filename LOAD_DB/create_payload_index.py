#!/usr/bin/env python3
"""
Create payload indexes on Qdrant collections for efficient filtering.

Creates indexes on three fields:
- filename (KEYWORD): Filter by PDF filename
- chunk_index (INTEGER): Filter by chunk position within document
- page (INTEGER): Filter by page number

Usage:
    python create_payload_index.py              # Index contextual collection (default)
    python create_payload_index.py --collection tro-child-1  # Index original collection
    python create_payload_index.py --collection my-collection  # Index custom collection
"""

import os
import sys
import logging
import argparse
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PayloadSchemaType
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_payload_index(collection_name: str) -> bool:
    """
    Create payload indexes on multiple fields for efficient filtering.

    Creates indexes on:
    - filename (KEYWORD): Filter by PDF filename
    - chunk_index (INTEGER): Filter by chunk position within document
    - page (INTEGER): Filter by page number

    Args:
        collection_name: Name of the Qdrant collection

    Returns:
        True if all indexes created successfully, False otherwise
    """
    try:
        # Initialize Qdrant client
        if not config.QDRANT_API_URL or not config.QDRANT_API_KEY:
            logger.error("QDRANT_API_URL and QDRANT_API_KEY must be set in environment")
            return False

        logger.info(f"Connecting to Qdrant at {config.QDRANT_API_URL}")
        client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

        # Verify collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name not in collection_names:
            logger.error(f"Collection '{collection_name}' does not exist")
            logger.info(f"Available collections: {collection_names}")
            return False

        logger.info(f"Found collection '{collection_name}'")

        # Get collection info before creating indexes
        collection_info = client.get_collection(collection_name)
        logger.info(f"Collection has {collection_info.points_count} points")

        # Define indexes to create
        indexes_to_create = [
            ('filename', PayloadSchemaType.KEYWORD),
            ('chunk_index', PayloadSchemaType.INTEGER),
            ('page', PayloadSchemaType.INTEGER),
        ]

        # Create each index with individual error handling
        success_count = 0
        failed_indexes = []

        for field_name, field_type in indexes_to_create:
            try:
                logger.info(f"Creating index on '{field_name}' ({field_type.value})...")
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                logger.info(f"✓ Index created: {field_name}")
                success_count += 1
            except Exception as e:
                logger.warning(f"✗ Failed to create index on '{field_name}': {e}")
                failed_indexes.append(field_name)

        # Report results
        if success_count == len(indexes_to_create):
            logger.info(f"✓ All {success_count} payload indexes created successfully")
            return True
        elif success_count > 0:
            logger.warning(f"Partial success: {success_count}/{len(indexes_to_create)} indexes created")
            logger.warning(f"Failed indexes: {failed_indexes}")
            return False
        else:
            logger.error("Failed to create any indexes")
            return False

    except Exception as e:
        logger.error(f"Error creating payload indexes: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Create payload indexes on Qdrant collections for efficient filtering"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=config.QDRANT_COLLECTION_NAME_CONTEXTUAL,
        help=f"Collection name (default: {config.QDRANT_COLLECTION_NAME_CONTEXTUAL})"
    )

    args = parser.parse_args()

    logger.info(f"Creating payload indexes on collection: {args.collection}")
    logger.info(f"Index fields: filename (KEYWORD), chunk_index (INTEGER), page (INTEGER)")

    success = create_payload_index(args.collection)

    if success:
        logger.info("\n✓ Index creation completed successfully")
        return 0
    else:
        logger.error("\n✗ Index creation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
