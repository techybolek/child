#!/usr/bin/env python
"""
Test script: Load a single PDF with new simplified context prompts.

Tests the new simplified prompts by loading just one PDF file.
"""

import os
import sys
import glob

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from load_pdf_qdrant import PDFToQdrantLoader
import config

def load_single_pdf(pdf_filename: str):
    """Load a single PDF with contextual mode."""

    # Initialize loader with contextual mode, clearing the collection
    loader = PDFToQdrantLoader(
        test_mode=False,
        max_pdfs=None,
        clear_collection=True,  # Clear to start fresh with new prompts
        contextual_mode=True
    )

    # Get the full path to the PDF
    pdf_path = os.path.join(config.PDFS_DIR, pdf_filename)

    if not os.path.exists(pdf_path):
        print(f"ERROR: PDF not found at {pdf_path}")
        print(f"\nAvailable PDFs in {config.PDFS_DIR}:")
        for pdf in sorted(glob.glob(os.path.join(config.PDFS_DIR, "*.pdf")))[:5]:
            print(f"  - {os.path.basename(pdf)}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Loading single PDF with new simplified context prompts")
    print(f"{'='*80}")
    print(f"PDF: {pdf_filename}")
    print(f"Collection: {loader.collection_name}")
    print(f"Mode: Contextual with simplified prompts")
    print(f"{'='*80}\n")

    # Clear and recreate collection
    loader.clear_and_recreate_collection()

    # Process the PDF
    documents = loader.process_pdf(pdf_path)

    if not documents:
        print("ERROR: No documents extracted from PDF")
        sys.exit(1)

    print(f"✓ Extracted {len(documents)} pages from PDF")

    # Upload to Qdrant
    loader.upload_documents_to_qdrant(documents)

    print(f"✓ Uploaded {len(documents)} chunks to Qdrant")

    # Print stats
    print(f"\n{'='*80}")
    print(f"Load complete!")
    print(f"  Total chunks: {loader.stats['total_chunks']}")
    print(f"  Collection: {loader.collection_name}")
    print(f"  Ready for testing...")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    pdf_name = "texas-early-learning-strategic-plan-2024-2026-final-accessible.pdf"
    load_single_pdf(pdf_name)
