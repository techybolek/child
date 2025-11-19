#!/usr/bin/env python3
"""
Qdrant File Exporter

Extracts all chunks for a specific PDF file from Qdrant vector database
and saves them to a plain text file.

Usage:
    python export_chunks.py "filename.pdf"

Example:
    python export_chunks.py "bcy-26-income-eligibility-and-maximum-psoc-twc.pdf"

Output:
    UTIL/[filename]_chunks.txt
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Configuration
COLLECTION_NAME = "tro-child-3-contextual"
OUTPUT_DIR = "UTIL"

def connect_to_qdrant():
    """Connect to Qdrant using environment variables."""
    api_url = os.getenv("QDRANT_API_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not api_url or not api_key:
        print("❌ Error: QDRANT_API_URL and QDRANT_API_KEY environment variables must be set")
        sys.exit(1)

    try:
        client = QdrantClient(url=api_url, api_key=api_key)
        return client
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        sys.exit(1)

def extract_chunks(client, filename):
    """
    Extract all chunks for a specific PDF file.

    Args:
        client: QdrantClient instance
        filename: PDF filename to search for

    Returns:
        List of tuples: (chunk_index, page_number, chunk_text, chunk_context, document_context, master_context)
        Sorted by chunk_index to maintain original document order
    """
    print(f"Searching for chunks with filename='{filename}'...")

    # Create filter for the specific document using filename field
    doc_filter = Filter(
        must=[
            FieldCondition(
                key="filename",
                match=MatchValue(value=filename)
            )
        ]
    )

    chunks = []
    offset = None

    # Scroll through all matching points
    while True:
        try:
            result = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=doc_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            points, next_offset = result

            if not points:
                break

            # Extract text, page number, chunk index, and contexts from each point
            for point in points:
                if 'text' in point.payload:
                    page_num = point.payload.get('page', 0)
                    chunk_idx = point.payload.get('chunk_index', 0)
                    chunk_text = point.payload['text']
                    chunk_context = point.payload.get('chunk_context', '')
                    document_context = point.payload.get('document_context', '')
                    master_context = point.payload.get('master_context', '')
                    chunks.append((chunk_idx, page_num, chunk_text, chunk_context, document_context, master_context))

            if next_offset is None:
                break

            offset = next_offset

        except Exception as e:
            print(f"❌ Error during scroll: {e}")
            sys.exit(1)

    # Sort chunks by chunk_index (maintains original document order)
    chunks.sort(key=lambda x: x[0])

    return chunks

def save_chunks(chunks, filename):
    """
    Save chunks to plain text file.

    Args:
        chunks: List of tuples (chunk_index, page_number, chunk_text, chunk_context, document_context, master_context)
        filename: Original PDF filename (for output naming)

    Returns:
        Tuple of (output_path, chunk_sizes)
    """
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate output filename
    base_name = filename.replace('.pdf', '')
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_chunks.txt")

    # Write master context at the beginning of the file (only once)
    master_context_written = False
    chunk_sizes = []

    # Write chunks to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk_idx, page_num, chunk_text, chunk_context, document_context, master_context in chunks:
                # Write master context at the beginning (only once)
                if not master_context_written and master_context:
                    f.write("=" * 80 + "\n")
                    f.write("MASTER CONTEXT (applies to all chunks)\n")
                    f.write("=" * 80 + "\n")
                    f.write(master_context)
                    f.write("\n\n")
                    f.write("=" * 80 + "\n\n")
                    master_context_written = True

                # Write document context at the beginning (only once, after master context)
                if chunk_idx == 0 and document_context:
                    f.write("DOCUMENT CONTEXT\n")
                    f.write("-" * 80 + "\n")
                    f.write(document_context)
                    f.write("\n\n")
                    f.write("=" * 80 + "\n\n")

                # Calculate chunk size
                char_count = len(chunk_text)
                word_count = len(chunk_text.split())
                chunk_sizes.append((char_count, word_count))

                # Use chunk_idx + 1 for display (0-indexed to 1-indexed)
                f.write(f"--- Chunk {chunk_idx + 1} (Page {page_num}) | {char_count} chars, {word_count} words ---\n")

                # Write chunk context if available
                if chunk_context:
                    f.write(f"\n[Chunk Context]: {chunk_context}\n\n")

                f.write(chunk_text)
                f.write("\n\n")

        return output_path, chunk_sizes
    except Exception as e:
        print(f"❌ Error writing to file: {e}")
        sys.exit(1)

def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python export_chunks.py 'filename.pdf'")
        print("\nExample:")
        print("  python export_chunks.py 'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf'")
        sys.exit(1)

    filename = sys.argv[1]

    print(f"\nQdrant File Exporter")
    print(f"{'=' * 60}")
    print(f"File: {filename}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"{'=' * 60}\n")

    # Connect to Qdrant
    print("Connecting to Qdrant...")
    client = connect_to_qdrant()

    # Extract chunks
    chunks = extract_chunks(client, filename)

    if not chunks:
        print(f"⚠️  No chunks found for '{filename}'")
        print("\nPossible reasons:")
        print("  - Filename spelling is incorrect (case-sensitive)")
        print("  - PDF was not loaded to the collection")
        print("  - Collection name is wrong")
        sys.exit(1)

    print(f"Found {len(chunks)} chunks")

    # Save to file
    output_path, chunk_sizes = save_chunks(chunks, filename)

    print(f"\n✅ Export complete!")
    print(f"📄 Saved to: {output_path}")
    print(f"📊 Total chunks: {len(chunks)}")

    # Get file size
    file_size = os.path.getsize(output_path)
    size_kb = file_size / 1024
    print(f"💾 File size: {size_kb:.1f} KB")

    # Display chunk size statistics
    if chunk_sizes:
        char_counts = [size[0] for size in chunk_sizes]
        word_counts = [size[1] for size in chunk_sizes]

        print(f"\n📏 Chunk Size Statistics:")
        print(f"   Characters - Min: {min(char_counts)}, Max: {max(char_counts)}, Avg: {sum(char_counts) / len(char_counts):.0f}")
        print(f"   Words      - Min: {min(word_counts)}, Max: {max(word_counts)}, Avg: {sum(word_counts) / len(word_counts):.0f}")

if __name__ == "__main__":
    main()
