#!/usr/bin/env python
"""Extract the first 5 chunks from Qdrant and save to files."""

from qdrant_client import QdrantClient
import config
import os

def extract_first_n_chunks(collection_name: str, n: int, output_dir: str):
    """Extract first N chunks from Qdrant and save to files."""

    client = QdrantClient(
        url=config.QDRANT_API_URL,
        api_key=config.QDRANT_API_KEY,
    )

    os.makedirs(output_dir, exist_ok=True)

    try:
        # Get collection info
        info = client.get_collection(collection_name)
        print(f"Collection: {collection_name}")
        print(f"Total points: {info.points_count}\n")

        # Scroll through points to find first N chunks
        limit = 100
        offset = 0
        chunks_found = 0

        while offset < info.points_count and chunks_found < n:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            for point in points:
                if chunks_found >= n:
                    break

                chunk_index = point.payload.get('chunk_index')
                chunk_text = point.payload.get('text', '')

                output_file = os.path.join(output_dir, f"chunk_{chunk_index}.txt")

                with open(output_file, 'w') as f:
                    f.write(chunk_text)

                print(f"✓ Chunk {chunk_index}: {len(chunk_text)} chars → {output_file}")
                chunks_found += 1

            offset = next_offset
            if next_offset == 0:
                break

        print(f"\n✓ Extracted {chunks_found} chunks to {output_dir}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    extract_first_n_chunks(
        collection_name="tro-child-1-contextual",
        n=5,
        output_dir="/home/tromanow/COHORT/TX/LOAD_DB/TMP"
    )
