"""Remove duplicate chunks from Qdrant collection"""
from qdrant_client import QdrantClient
import os
from collections import defaultdict

def remove_duplicates(collection_name):
    client = QdrantClient(
        url=os.getenv('QDRANT_API_URL'),
        api_key=os.getenv('QDRANT_API_KEY')
    )
    
    print(f"Scanning collection: {collection_name}")
    
    # Collect all points
    offset = None
    all_points = []
    
    while True:
        points, offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset
        )
        
        if not points:
            break
        
        all_points.extend(points)
        
        if offset is None:
            break
    
    print(f"Total points: {len(all_points)}")
    
    # Find duplicates (keep first occurrence)
    seen_texts = {}
    duplicates_to_delete = []
    
    for point in all_points:
        text = point.payload.get('text', '')
        if text in seen_texts:
            # Duplicate found
            duplicates_to_delete.append(point.id)
        else:
            seen_texts[text] = point.id
    
    print(f"Unique texts: {len(seen_texts)}")
    print(f"Duplicates to delete: {len(duplicates_to_delete)}")
    
    if duplicates_to_delete:
        confirm = input(f"\nDelete {len(duplicates_to_delete)} duplicate points? (yes/no): ")
        if confirm.lower() == 'yes':
            # Delete in batches
            batch_size = 100
            for i in range(0, len(duplicates_to_delete), batch_size):
                batch = duplicates_to_delete[i:i+batch_size]
                client.delete(
                    collection_name=collection_name,
                    points_selector=batch
                )
                print(f"Deleted batch {i//batch_size + 1}/{(len(duplicates_to_delete)-1)//batch_size + 1}")
            
            print(f"\n✓ Deleted {len(duplicates_to_delete)} duplicates")
        else:
            print("Cancelled")
    else:
        print("No duplicates found!")

if __name__ == '__main__':
    remove_duplicates('tro-child-3-contextual')
