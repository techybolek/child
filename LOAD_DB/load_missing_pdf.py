#!/usr/bin/env python
"""
Load a single missing PDF to the existing collection WITHOUT clearing it.

Usage:
    python load_missing_pdf.py

This script will APPEND the missing PDF to the existing tro-child-3-contextual collection.
It will NOT delete or modify any existing data.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from load_pdf_qdrant import PDFToQdrantLoader
import config

def load_missing_pdf():
    """Load the missing PDF without clearing the collection."""

    pdf_filename = "tx-ccdf-state-plan-ffy2025-2027-approved.pdf"

    print(f"\n{'='*80}")
    print(f"Loading Missing PDF - APPEND MODE (Collection will NOT be cleared)")
    print(f"{'='*80}")
    print(f"PDF: {pdf_filename}")
    print(f"Collection: {config.QDRANT_COLLECTION_NAME_CONTEXTUAL}")
    print(f"Mode: Contextual (with previous-chunk-context)")
    print(f"{'='*80}\n")

    # Verify PDF exists
    pdf_path = os.path.join(config.PDFS_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)

    print(f"✓ Found PDF at {pdf_path}")

    # Initialize loader with APPEND mode (clear_collection=False)
    print(f"\nInitializing loader in APPEND mode...")
    loader = PDFToQdrantLoader(
        test_mode=False,
        max_pdfs=None,
        clear_collection=False,  # CRITICAL: Do NOT clear existing collection
        contextual_mode=True
    )

    print(f"✓ Loader initialized (collection will NOT be cleared)")

    # Get current collection stats
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=config.QDRANT_API_URL, api_key=config.QDRANT_API_KEY)
        collection_info = client.get_collection(config.QDRANT_COLLECTION_NAME_CONTEXTUAL)
        chunks_before = collection_info.points_count
        print(f"\n✓ Current collection has {chunks_before} chunks")
    except Exception as e:
        print(f"\n⚠ Could not get collection stats: {e}")
        chunks_before = None

    # Process the PDF
    print(f"\nProcessing PDF...")
    documents = loader.process_pdf(pdf_path)

    if not documents:
        print("ERROR: No documents extracted from PDF")
        sys.exit(1)

    print(f"✓ Extracted {len(documents)} chunks from PDF")

    # Upload to Qdrant (APPENDING to existing collection)
    print(f"\nUploading chunks to collection (appending)...")
    loader.upload_documents_to_qdrant(documents)

    print(f"✓ Uploaded {len(documents)} chunks to collection")

    # Get updated collection stats
    if chunks_before is not None:
        try:
            collection_info = client.get_collection(config.QDRANT_COLLECTION_NAME_CONTEXTUAL)
            chunks_after = collection_info.points_count
            chunks_added = chunks_after - chunks_before
            print(f"\n✓ Collection now has {chunks_after} chunks (+{chunks_added} added)")
        except Exception as e:
            print(f"\n⚠ Could not get updated collection stats: {e}")

    # Print summary
    print(f"\n{'='*80}")
    print(f"Load Complete!")
    print(f"  PDF: {pdf_filename}")
    print(f"  Chunks added: {len(documents)}")
    print(f"  Collection: {config.QDRANT_COLLECTION_NAME_CONTEXTUAL}")
    print(f"  Mode: APPEND (existing data preserved)")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    load_missing_pdf()
