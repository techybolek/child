#!/usr/bin/env python
"""Extract a sample chunk from Qdrant for inspection."""

import json
from qdrant_client import QdrantClient
import config

def extract_chunk(collection_name: str, chunk_index: int, output_file: str):
    """Extract a specific chunk from Qdrant and save to file."""

    client = QdrantClient(
        url=config.QDRANT_API_URL,
        api_key=config.QDRANT_API_KEY,
    )

    try:
        # Get collection info
        info = client.get_collection(collection_name)
        print(f"Collection: {collection_name}")
        print(f"Total points: {info.points_count}")

        # Scroll through points to find chunks with matching chunk_index
        limit = 100
        offset = 0
        found = False

        while offset < info.points_count:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            for point in points:
                if point.payload.get('chunk_index') == chunk_index:
                    # Found the chunk
                    chunk_text = point.payload.get('text', '')
                    chunk_metadata = {
                        'id': point.id,
                        'chunk_index': point.payload.get('chunk_index'),
                        'page': point.payload.get('page'),
                        'filename': point.payload.get('filename'),
                        'has_context': point.payload.get('has_context'),
                    }

                    # Save to file
                    with open(output_file, 'w') as f:
                        f.write(chunk_text)

                    print(f"\n✓ Extracted chunk {chunk_index}")
                    print(f"  File: {output_file}")
                    print(f"  Metadata: {chunk_metadata}")
                    print(f"  Size: {len(chunk_text)} characters")

                    found = True
                    return

            offset = next_offset
            if next_offset == 0:
                break

        if not found:
            print(f"ERROR: Chunk {chunk_index} not found in collection")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Extract chunk 2 (third chunk, since 0-indexed)
    extract_chunk(
        collection_name="tro-child-1-contextual",
        chunk_index=2,
        output_file="/home/tromanow/COHORT/TX/LOAD_DB/TMP/chunk_3_new_format.txt"
    )
