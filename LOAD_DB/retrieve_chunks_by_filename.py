#!/usr/bin/env python3
"""
Retrieve all chunks from a specific PDF file in Qdrant.

Usage:
    python retrieve_chunks_by_filename.py
    # Uses default: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

    python retrieve_chunks_by_filename.py --filename "child-care-services-guide-twc.pdf"
    # Retrieves chunks from specified file

    python retrieve_chunks_by_filename.py --output chunks.json
    # Saves results to JSON file
"""

import os
import sys
import json
import logging
import argparse
from typing import List, Optional
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError as e:
    raise ImportError(f"Required libraries missing: {e}\nInstall with: pip install -r requirements.txt")

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class ChunkRetriever:
    """Retrieve chunks from Qdrant filtered by filename."""

    def __init__(self, collection_name: str = config.QDRANT_COLLECTION_NAME_CONTEXTUAL):
        """Initialize Qdrant client."""
        if not config.QDRANT_API_URL or not config.QDRANT_API_KEY:
            raise ValueError("QDRANT_API_URL and QDRANT_API_KEY must be set in environment")

        logger.info(f"Connecting to Qdrant at {config.QDRANT_API_URL}")
        self.client = QdrantClient(
            url=config.QDRANT_API_URL,
            api_key=config.QDRANT_API_KEY,
        )
        self.collection_name = collection_name

    def retrieve_by_filename(self, filename: str) -> List[dict]:
        """
        Retrieve all chunks from a specific PDF file.

        Args:
            filename: Name of the PDF file (e.g., "child-care-services-guide-twc.pdf")

        Returns:
            List of chunks sorted by chunk_index
        """
        logger.info(f"Retrieving chunks from '{filename}'...")

        all_chunks = []
        offset = None
        batch_count = 0

        while True:
            batch_count += 1
            logger.debug(f"Fetching batch {batch_count}...")

            # Scroll through filtered points
            try:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key='filename',
                                match=models.MatchValue(value=filename)
                            )
                        ]
                    ),
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
            except Exception as e:
                logger.error(f"Error querying Qdrant: {e}")
                raise

            if not points:
                logger.warning(f"No chunks found for filename: {filename}")
                break

            all_chunks.extend(points)
            logger.debug(f"  Batch {batch_count}: Retrieved {len(points)} points")

            # Check if we've reached the end
            if next_offset is None or len(points) == 0:
                break

            offset = next_offset

        # Sort by chunk_index to restore document order
        all_chunks.sort(key=lambda p: p.payload.get('chunk_index', 0))

        logger.info(f"✓ Retrieved {len(all_chunks)} chunks from '{filename}'")
        return all_chunks

    def format_chunks_display(self, points: List) -> str:
        """Format chunks for console display."""
        if not points:
            return "No chunks found."

        output = []
        output.append(f"\n{'=' * 80}")
        output.append(f"RETRIEVED CHUNKS: {len(points)} total")
        output.append(f"{'=' * 80}\n")

        for point in points:
            payload = point.payload
            chunk_idx = payload.get('chunk_index', 0)
            total = payload.get('total_chunks', 1)
            page = payload.get('page', 'N/A')
            text_preview = payload.get('text', '')[:150]

            output.append(f"Chunk {chunk_idx + 1}/{total} (Page {page})")
            output.append(f"  Point ID: {point.id}")
            output.append(f"  Text: {text_preview}...")

            # Show context info if available
            if payload.get('has_context'):
                output.append(f"  [Contextual metadata available]")

            output.append("")

        output.append(f"{'=' * 80}\n")
        return "\n".join(output)

    def save_to_json(self, points: List, output_path: str) -> None:
        """Save chunks to JSON file."""
        data = {
            'metadata': {
                'filename': points[0].payload.get('filename') if points else None,
                'total_chunks': len(points),
                'retrieved_at': datetime.now().isoformat(),
                'collection': self.collection_name
            },
            'chunks': []
        }

        for point in points:
            payload = point.payload
            data['chunks'].append({
                'id': point.id,
                'chunk_index': payload.get('chunk_index'),
                'total_chunks': payload.get('total_chunks'),
                'page': payload.get('page'),
                'text': payload.get('text'),
                'filename': payload.get('filename'),
                'source_url': payload.get('source_url'),
                'has_context': payload.get('has_context', False),
                'master_context': payload.get('master_context'),
                'document_context': payload.get('document_context'),
                'chunk_context': payload.get('chunk_context'),
            })

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✓ Saved {len(points)} chunks to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Retrieve all chunks from a specific PDF file in Qdrant'
    )
    parser.add_argument(
        '--filename',
        type=str,
        default='bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
        help='PDF filename to retrieve chunks from (default: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf)'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default=config.QDRANT_COLLECTION_NAME_CONTEXTUAL,
        help=f'Qdrant collection name (default: {config.QDRANT_COLLECTION_NAME_CONTEXTUAL})'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save results to JSON file (optional)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output'
    )

    args = parser.parse_args()

    try:
        retriever = ChunkRetriever(collection_name=args.collection)
        chunks = retriever.retrieve_by_filename(args.filename)

        if not args.quiet:
            display = retriever.format_chunks_display(chunks)
            print(display)

        # Save to JSON if requested
        if args.output:
            retriever.save_to_json(chunks, args.output)

        return 0 if chunks else 1

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
