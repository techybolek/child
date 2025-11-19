#!/usr/bin/env python3
"""
Export all chunks from a specific PDF in Qdrant to a text file.
"""
import os
import sys
from qdrant_client import QdrantClient

def export_chunks(pdf_filename: str, collection_name: str = "tro-child-3-contextual"):
    """Export all chunks from a PDF to a text file."""

    # Connect to Qdrant
    client = QdrantClient(
        url=os.getenv("QDRANT_API_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )

    print(f"Exporting chunks from: {pdf_filename}")
    print(f"Collection: {collection_name}")
    print("=" * 80)

    # Scroll through all points to find matching chunks
    chunks = []
    offset = None

    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        points, offset = result

        if not points:
            break

        for point in points:
            # Check both 'filename' (new loader) and 'source' (reload script) fields
            doc_field = point.payload.get('filename') or point.payload.get('source', '')
            if pdf_filename in doc_field:
                chunks.append({
                    'page': point.payload.get('page', 0),
                    'chunk_index': point.payload.get('chunk_index', 0),
                    'text': point.payload.get('text', ''),
                    'chunk_context': point.payload.get('chunk_context', ''),
                    'document_context': point.payload.get('document_context', ''),
                    'master_context': point.payload.get('master_context', '')
                })

        if offset is None:
            break

    print(f"Found {len(chunks)} chunks")

    if not chunks:
        print(f"No chunks found for {pdf_filename}")
        return

    # Sort by page number, then chunk index for proper ordering
    chunks.sort(key=lambda x: (x['page'], x['chunk_index']))

    # Output filename
    output_file = f"{pdf_filename.replace('.pdf', '')}_chunks.txt"
    output_path = os.path.join(os.path.dirname(__file__), output_file)

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write contexts at beginning
        if chunks[0]['master_context']:
            f.write("=" * 80 + "\n")
            f.write("MASTER CONTEXT\n")
            f.write("=" * 80 + "\n")
            f.write(chunks[0]['master_context'] + "\n\n")

        if chunks[0]['document_context']:
            f.write("=" * 80 + "\n")
            f.write("DOCUMENT CONTEXT\n")
            f.write("=" * 80 + "\n")
            f.write(chunks[0]['document_context'] + "\n\n")

        f.write("=" * 80 + "\n")
        f.write(f"CHUNKS ({len(chunks)} total)\n")
        f.write("=" * 80 + "\n\n")

        # Write each chunk
        for i, chunk in enumerate(chunks, 1):
            chunk_size = len(chunk['text'])
            f.write("-" * 80 + "\n")
            f.write(f"Chunk {i} (Page {chunk['page']}, {chunk_size} chars)\n")
            f.write("-" * 80 + "\n")

            if chunk['chunk_context']:
                f.write(f"[Chunk Context]: {chunk['chunk_context']}\n\n")

            f.write(chunk['text'] + "\n\n")

    print(f"✅ Exported to: {output_path}")
    print(f"📊 Total chunks: {len(chunks)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_chunks_from_qdrant.py <pdf_filename>")
        sys.exit(1)

    pdf_filename = sys.argv[1]
    export_chunks(pdf_filename)
