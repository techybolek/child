#!/usr/bin/env python3
"""
Create payload indexes on Qdrant collections for efficient filtering.

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
    Create a payload index on the 'filename' field for efficient filtering.

    Args:
        collection_name: Name of the Qdrant collection

    Returns:
        True if successful, False otherwise
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

        # Get collection info before creating index
        collection_info = client.get_collection(collection_name)
        logger.info(f"Collection has {collection_info.points_count} points")

        # Create payload index on filename field
        logger.info("Creating payload index on 'filename' field...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name='filename',
            field_schema=PayloadSchemaType.KEYWORD
        )
        logger.info(f"✓ Payload index created successfully on '{collection_name}' collection")
        return True

    except Exception as e:
        logger.error(f"Error creating payload index: {e}")
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

    logger.info(f"Creating payload index on collection: {args.collection}")
    logger.info(f"Index field: 'filename' (type: KEYWORD)")

    success = create_payload_index(args.collection)

    if success:
        logger.info("\n✓ Index creation completed successfully")
        return 0
    else:
        logger.error("\n✗ Index creation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
