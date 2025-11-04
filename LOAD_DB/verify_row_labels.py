"""Verify that BCY-26 chunks contain row labels (e.g., '12')."""

from qdrant_client import QdrantClient
import config

client = QdrantClient(url=config.QDRANT_API_URL, api_key=config.QDRANT_API_KEY)

# Scroll through and find BCY-26 chunks
result = client.scroll(
    collection_name='tro-child-3-contextual',
    limit=100,
    with_payload=True,
    with_vectors=False
)

print("\n" + "="*70)
print("VERIFYING BCY-26 CHUNKS CONTAIN ROW LABELS")
print("="*70 + "\n")

points = result[0]
bcy26_chunks = []

for point in points:
    if point.payload.get('doc') == 'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf':
        bcy26_chunks.append(point)

print(f"Found {len(bcy26_chunks)} BCY-26 chunks\n")

for i, point in enumerate(bcy26_chunks, 1):
    text = point.payload.get('text', '')
    print(f"\n{'='*70}")
    print(f"Chunk {i} (page {point.payload.get('page')})")
    print('='*70)
    print(text[:600])  # First 600 chars
    if len(text) > 600:
        print('...')

    # Check for row labels
    has_12 = '12' in text or '12\n' in text
    has_dollar = '$' in text

    if has_12 and has_dollar:
        print("\n✓ SUCCESS: Contains '12' and '$' - Row label preserved!")
    elif has_dollar:
        print("\n⚠ Contains '$' but no '12' - May not have family size 12 data")

    print()

print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70 + "\n")
