#!/usr/bin/env python3
"""
Retrieve chunks from a specific PDF file in Qdrant with optional filtering.

Usage:
    python retrieve_chunks_by_filename.py
    # Uses default: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

    python retrieve_chunks_by_filename.py --filename "child-care-services-guide-twc.pdf"
    # Retrieves all chunks from specified file

    python retrieve_chunks_by_filename.py --filename "doc.pdf" --chunk 5
    # Retrieves only chunk #5 from the file (0-indexed)

    python retrieve_chunks_by_filename.py --filename "doc.pdf" --text-length 1000
    # Show 1000 characters of text per chunk

    python retrieve_chunks_by_filename.py --filename "doc.pdf" --text-length -1
    # Show full text (no truncation)

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

    def retrieve_by_filename(self, filename: str, chunk_index: Optional[int] = None) -> List[dict]:
        """
        Retrieve all chunks from a specific PDF file.

        Args:
            filename: Name of the PDF file (e.g., "child-care-services-guide-twc.pdf")
            chunk_index: Optional specific chunk index to retrieve (0-indexed)

        Returns:
            List of chunks sorted by chunk_index
        """
        if chunk_index is not None:
            logger.info(f"Retrieving chunk {chunk_index} from '{filename}'...")
        else:
            logger.info(f"Retrieving chunks from '{filename}'...")

        all_chunks = []
        offset = None
        batch_count = 0

        # Scroll through all points and filter client-side
        # Check both 'doc' and 'filename' fields for backward compatibility
        while True:
            batch_count += 1
            logger.debug(f"Fetching batch {batch_count}...")

            # Scroll through all points (no server-side filter)
            try:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
            except Exception as e:
                logger.error(f"Error querying Qdrant: {e}")
                raise

            if not points:
                break

            # Filter client-side for matching filename
            for point in points:
                if point.payload:
                    doc_value = point.payload.get('doc', '')
                    filename_value = point.payload.get('filename', '')
                    if doc_value == filename or filename_value == filename:
                        all_chunks.append(point)

            logger.debug(f"  Batch {batch_count}: Found {len([p for p in points if p.payload and (p.payload.get('doc') == filename or p.payload.get('filename') == filename)])} matching points")

            # Check if we've reached the end
            if next_offset is None or len(points) == 0:
                break

            offset = next_offset

        # Check if we found any chunks
        if not all_chunks:
            logger.warning(f"No chunks found for filename: {filename}")

        # Sort by chunk_index to restore document order
        all_chunks.sort(key=lambda p: p.payload.get('chunk_index', 0))

        # Filter by chunk_index client-side if specified
        if chunk_index is not None:
            all_chunks = [p for p in all_chunks if p.payload.get('chunk_index') == chunk_index]
            logger.info(f"✓ Retrieved chunk {chunk_index} from '{filename}'")
        else:
            logger.info(f"✓ Retrieved {len(all_chunks)} chunks from '{filename}'")

        return all_chunks

    def format_chunks_display(self, points: List, text_length: int = 500) -> str:
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
            filename = payload.get('filename', 'Unknown')
            text = payload.get('text', '')
            text_preview = text if len(text) <= text_length else text[:text_length] + '...'

            output.append(f"Chunk {chunk_idx}/{total} - Page {page}")
            output.append(f"Filename: {filename}")
            output.append(f"Point ID: {point.id}")
            output.append("-" * 80)
            output.append(f"Text:\n{text_preview}")
            output.append("-" * 80)

            # Show context content if available
            if payload.get('has_context'):
                doc_context = payload.get('document_context')
                chunk_context = payload.get('chunk_context')

                if doc_context:
                    output.append(f"Document Context:\n{doc_context}")
                if chunk_context:
                    output.append(f"Chunk Context:\n{chunk_context}")

                if doc_context or chunk_context:
                    output.append("-" * 80)

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
        description='Retrieve chunks from a specific PDF file in Qdrant'
    )
    parser.add_argument(
        '--filename',
        type=str,
        default='bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
        help='PDF filename to retrieve chunks from (default: bcy-26-income-eligibility-and-maximum-psoc-twc.pdf)'
    )
    parser.add_argument(
        '--chunk',
        '-c',
        type=int,
        help='Specific chunk index to retrieve (0-indexed, optional)'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default=config.QDRANT_COLLECTION_NAME_CONTEXTUAL,
        help=f'Qdrant collection name (default: {config.QDRANT_COLLECTION_NAME_CONTEXTUAL})'
    )
    parser.add_argument(
        '--text-length',
        type=int,
        default=500,
        help='Maximum characters to display for chunk text (default: 500, use -1 for full text)'
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
        chunks = retriever.retrieve_by_filename(args.filename, chunk_index=args.chunk)

        if not args.quiet:
            text_length = None if args.text_length == -1 else args.text_length
            display = retriever.format_chunks_display(chunks, text_length=text_length or 999999)
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
