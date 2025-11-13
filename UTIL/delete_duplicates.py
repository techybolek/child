"""Delete duplicate chunks - keep version with 'filename' field."""
import os
import sys
from collections import defaultdict
from qdrant_client import QdrantClient

QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = 'tro-child-3-contextual'


def delete_duplicates(confirm=False):
    """Delete duplicate chunks intelligently."""
    client = QdrantClient(url=QDRANT_API_URL, api_key=QDRANT_API_KEY)

    print("Scanning for duplicate chunks...")
    print()

    # Track chunks by text content
    text_to_points = defaultdict(list)
    offset = None
    batch_size = 100

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
            filename = point.payload.get('filename', '')
            source = point.payload.get('source', 'unknown')

            text_to_points[text].append({
                'id': point.id,
                'has_filename': bool(filename),
                'filename': filename,
                'source': source,
                'page': point.payload.get('page', 'N/A'),
                'text_preview': text[:100]
            })

        if offset is None:
            break

    # Find duplicates
    duplicates = {text: points for text, points in text_to_points.items() if len(points) > 1}

    if not duplicates:
        print("✓ No duplicates found!")
        return

    print(f"Found {len(duplicates)} duplicate chunks")
    print()

    # Decide which copies to delete
    points_to_delete = []
    duplicate_summary = []

    for text, points in duplicates.items():
        # Strategy: Keep the one WITH filename, delete the one WITHOUT
        points_with_filename = [p for p in points if p['has_filename']]
        points_without_filename = [p for p in points if not p['has_filename']]

        if points_without_filename:
            # Delete all copies without filename
            points_to_delete.extend(points_without_filename)
            duplicate_summary.append({
                'text_preview': text[:80],
                'total_copies': len(points),
                'deleting': len(points_without_filename),
                'keeping': len(points_with_filename),
                'strategy': 'Delete copies without filename field'
            })
        elif len(points) > 1:
            # All have filename (or all don't) - keep first, delete rest
            points_to_delete.extend(points[1:])
            duplicate_summary.append({
                'text_preview': text[:80],
                'total_copies': len(points),
                'deleting': len(points) - 1,
                'keeping': 1,
                'strategy': 'Keep first, delete rest (all have same metadata)'
            })

    # Display summary
    print("Deletion Plan:")
    print("=" * 80)
    for i, dup in enumerate(duplicate_summary, 1):
        print(f"\n{i}. Text: {dup['text_preview']}...")
        print(f"   Total copies: {dup['total_copies']}")
        print(f"   Will delete: {dup['deleting']}")
        print(f"   Will keep: {dup['keeping']}")
        print(f"   Strategy: {dup['strategy']}")

    print()
    print("=" * 80)
    print(f"Total points to delete: {len(points_to_delete)}")
    print()

    # Show first few points to delete
    print("Points to be deleted (first 10):")
    for i, point in enumerate(points_to_delete[:10], 1):
        print(f"{i}. ID: {point['id']}")
        print(f"   Has filename: {point['has_filename']}")
        print(f"   Filename: {point['filename'] or '(empty)'}")
        print(f"   Source: {point['source']}")
        print(f"   Text: {point['text_preview']}...")
        print()

    # Confirm deletion
    if not confirm:
        try:
            response = input(f"Delete {len(points_to_delete)} duplicate points? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return

    # Delete points
    print(f"\nDeleting {len(points_to_delete)} points...")
    ids_to_delete = [point['id'] for point in points_to_delete]

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=ids_to_delete
    )

    print(f"✓ Deleted {len(points_to_delete)} duplicate points")

    # Verify
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"✓ Collection now has {collection_info.points_count} points")


if __name__ == '__main__':
    confirm = '--confirm' in sys.argv
    delete_duplicates(confirm=confirm)
