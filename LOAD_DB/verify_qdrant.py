"""
Verify Qdrant collection and test queries
"""

import os
import sys
import logging
from typing import List, Dict, Any

# Add parent directory to path to import SCRAPER module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from qdrant_client import QdrantClient
    from langchain_openai import OpenAIEmbeddings
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

from SCRAPER import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QdrantVerifier:
    """Verify and test Qdrant collection."""

    def __init__(self):
        """Initialize Qdrant verifier."""
        if not config.QDRANT_API_URL or not config.QDRANT_API_KEY:
            raise ValueError("QDRANT_API_URL and QDRANT_API_KEY must be set")

        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set")

        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )

        self.embeddings = OpenAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            openai_api_key=config.OPENAI_API_KEY
        )

    def check_collection_exists(self) -> bool:
        """Check if collection exists."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            exists = config.QDRANT_COLLECTION_NAME in collection_names

            if exists:
                logger.info(f"✓ Collection '{config.QDRANT_COLLECTION_NAME}' exists")
            else:
                logger.warning(f"✗ Collection '{config.QDRANT_COLLECTION_NAME}' does not exist")

            return exists
        except Exception as e:
            logger.error(f"Error checking collection: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection_info = self.client.get_collection(config.QDRANT_COLLECTION_NAME)

            stats = {
                'points_count': collection_info.points_count,
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'status': collection_info.status
            }

            logger.info("\nCollection Statistics:")
            logger.info(f"  Total Points: {stats['points_count']:,}")
            logger.info(f"  Total Vectors: {stats['vectors_count']:,}")
            logger.info(f"  Indexed Vectors: {stats['indexed_vectors_count']:,}")
            logger.info(f"  Status: {stats['status']}")

            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}

    def sample_data(self, limit: int = 5):
        """Sample random data from collection."""
        try:
            logger.info(f"\nSampling {limit} random points:")

            # Scroll to get some points
            points, _ = self.client.scroll(
                collection_name=config.QDRANT_COLLECTION_NAME,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            for i, point in enumerate(points, 1):
                logger.info(f"\nPoint {i} (ID: {point.id}):")
                logger.info(f"  Filename: {point.payload.get('filename', 'N/A')}")
                logger.info(f"  Source URL: {point.payload.get('source_url', 'N/A')}")
                logger.info(f"  Page: {point.payload.get('page_number', 'N/A')}")
                logger.info(f"  Chunk: {point.payload.get('chunk_index', 'N/A')}/{point.payload.get('total_chunks', 'N/A')}")
                text_preview = point.payload.get('text', '')[:100]
                logger.info(f"  Text Preview: {text_preview}...")

        except Exception as e:
            logger.error(f"Error sampling data: {e}")

    def test_search(self, query: str, limit: int = 3):
        """Test semantic search."""
        try:
            logger.info(f"\nTesting search with query: '{query}'")

            # Generate query embedding
            query_vector = self.embeddings.embed_query(query)

            # Search
            results = self.client.search(
                collection_name=config.QDRANT_COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )

            logger.info(f"Found {len(results)} results:\n")

            for i, result in enumerate(results, 1):
                logger.info(f"Result {i} (Score: {result.score:.4f}):")
                logger.info(f"  Filename: {result.payload.get('filename', 'N/A')}")
                logger.info(f"  Page: {result.payload.get('page_number', 'N/A')}")
                logger.info(f"  Source: {result.payload.get('source_url', 'N/A')}")
                text_preview = result.payload.get('text', '')[:200]
                logger.info(f"  Text: {text_preview}...\n")

        except Exception as e:
            logger.error(f"Error testing search: {e}")

    def get_unique_sources(self):
        """Get unique PDF sources in collection."""
        try:
            # Get all points (or sample if too many)
            points, _ = self.client.scroll(
                collection_name=config.QDRANT_COLLECTION_NAME,
                limit=10000,  # Adjust if you have more
                with_payload=True,
                with_vectors=False
            )

            filenames = set()
            for point in points:
                filename = point.payload.get('filename')
                if filename:
                    filenames.add(filename)

            logger.info(f"\nUnique PDF files in collection: {len(filenames)}")
            for filename in sorted(filenames):
                logger.info(f"  - {filename}")

        except Exception as e:
            logger.error(f"Error getting unique sources: {e}")

    def run_verification(self):
        """Run full verification."""
        logger.info("=" * 60)
        logger.info("Qdrant Collection Verification")
        logger.info("=" * 60)

        # Check collection exists
        if not self.check_collection_exists():
            logger.error("Collection does not exist. Run load_pdf_qdrant.py first.")
            return

        # Get stats
        self.get_collection_stats()

        # Sample data
        self.sample_data(limit=3)

        # Get unique sources
        self.get_unique_sources()

        # Test searches
        test_queries = [
            "What are the eligibility requirements for child care assistance?",
            "How do I apply for child care services in Texas?",
            "What is the Texas Rising Star program?"
        ]

        for query in test_queries:
            self.test_search(query, limit=2)

        logger.info("\n" + "=" * 60)
        logger.info("Verification Complete!")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    verifier = QdrantVerifier()
    verifier.run_verification()


if __name__ == '__main__':
    main()
