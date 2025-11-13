"""Find duplicate chunks in Qdrant collection."""
import os
from collections import defaultdict
from qdrant_client import QdrantClient

# Configuration
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = 'tro-child-3-contextual'


def find_duplicates():
    """Scan entire collection for duplicate chunks."""
    client = QdrantClient(url=QDRANT_API_URL, api_key=QDRANT_API_KEY)

    # Get collection info
    collection_info = client.get_collection(COLLECTION_NAME)
    total_points = collection_info.points_count
    print(f"Scanning {total_points} points in collection '{COLLECTION_NAME}'...")
    print()

    # Track chunks by text content
    text_to_points = defaultdict(list)

    # Scroll through all points
    offset = None
    batch_size = 100
    processed = 0

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        if not points:
            break

        for point in points:
            text = point.payload.get('text', '')
            filename = point.payload.get('filename', point.payload.get('doc', 'unknown'))
            page = point.payload.get('page', 'N/A')

            text_to_points[text].append({
                'id': str(point.id),
                'filename': filename,
                'page': page,
                'text_preview': text[:100]
            })

        processed += len(points)
        print(f"Processed {processed}/{total_points} points...", end='\r')

        if offset is None:
            break

    print()
    print()

    # Find duplicates
    duplicates = {text: points for text, points in text_to_points.items() if len(points) > 1}

    if not duplicates:
        print("✓ No duplicates found!")
        return

    # Report duplicates
    print(f"❌ Found {len(duplicates)} duplicate chunks:")
    print("=" * 80)

    for i, (text, points) in enumerate(duplicates.items(), 1):
        print(f"\nDuplicate #{i}: {len(points)} copies")
        print(f"Text preview: {text[:200]}...")
        print(f"\nLocations:")
        for point in points:
            print(f"  - ID: {point['id']}")
            print(f"    File: {point['filename']}")
            print(f"    Page: {point['page']}")
        print("-" * 80)

    # Summary
    total_duplicate_points = sum(len(points) - 1 for points in duplicates.values())
    print(f"\nSummary:")
    print(f"  Total unique chunks with duplicates: {len(duplicates)}")
    print(f"  Total excess duplicate points: {total_duplicate_points}")
    print(f"  Storage waste: {total_duplicate_points}/{total_points} ({100*total_duplicate_points/total_points:.1f}%)")


if __name__ == '__main__':
    find_duplicates()
