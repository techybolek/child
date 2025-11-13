"""Inspect the specific duplicate chunk causing evaluation failure."""
import os
from qdrant_client import QdrantClient

QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = 'tro-child-3-contextual'

client = QdrantClient(url=QDRANT_API_URL, api_key=QDRANT_API_KEY)

# The two duplicate IDs from the Vietnamese chunk
duplicate_ids = [98448687436107150, 8492973850440138611]

print("Inspecting duplicate Vietnamese chunk...")
print("=" * 80)

for point_id in duplicate_ids:
    point = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[point_id],
        with_payload=True,
        with_vectors=False
    )[0]

    print(f"\nPoint ID: {point_id}")
    print(f"Payload keys: {list(point.payload.keys())}")
    print(f"\nFull payload:")
    for key, value in point.payload.items():
        if key == 'text':
            print(f"  {key}: {value[:100]}...")
        else:
            print(f"  {key}: {value}")
    print("-" * 80)
