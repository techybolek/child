#!/usr/bin/env python3
"""
Generate Bedrock KB metadata files from scraper metadata.

Reads: scraped_content/raw/pdfs/*_pdf.json
Writes: bedrock_metadata/{filename}.metadata.json

Each metadata file follows Bedrock schema:
{
    "metadataAttributes": {
        "source_url": "https://www.twc.texas.gov/..."
    }
}

Usage:
    python generate_bedrock_metadata.py
    python generate_bedrock_metadata.py --output-dir ./custom_output
    python generate_bedrock_metadata.py --dry-run
"""

import argparse
import glob
import json
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_scraper_metadata(pdfs_dir: str) -> list[dict]:
    """Load all PDF metadata from scraper JSON files.

    Args:
        pdfs_dir: Directory containing *_pdf.json files

    Returns:
        List of metadata dicts with filename and source_url
    """
    metadata_files = glob.glob(os.path.join(pdfs_dir, "*_pdf.json"))
    results = []

    for json_path in sorted(metadata_files):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            filename = data.get('filename')
            source_url = data.get('source_url')

            if filename and source_url:
                results.append({
                    'filename': filename,
                    'source_url': source_url,
                    'pdf_id': data.get('pdf_id', ''),
                    'json_path': json_path
                })
            else:
                print(f"[WARN] Missing filename or source_url in {json_path}")

        except Exception as e:
            print(f"[ERROR] Failed to load {json_path}: {e}")

    return results


def generate_bedrock_metadata(metadata: dict) -> dict:
    """Generate Bedrock KB metadata schema from scraper metadata.

    Args:
        metadata: Dict with filename and source_url

    Returns:
        Bedrock metadata dict with metadataAttributes
    """
    return {
        "metadataAttributes": {
            "source_url": metadata['source_url']
        }
    }


def write_metadata_file(output_dir: str, filename: str, bedrock_metadata: dict, dry_run: bool = False) -> str:
    """Write Bedrock metadata file to output directory.

    Args:
        output_dir: Directory to write metadata files
        filename: PDF filename (e.g., "wd-24-23-att1-twc.pdf")
        bedrock_metadata: Bedrock metadata dict
        dry_run: If True, don't write file

    Returns:
        Path to written metadata file
    """
    # Bedrock expects: {filename}.metadata.json
    metadata_filename = f"{filename}.metadata.json"
    output_path = os.path.join(output_dir, metadata_filename)

    if dry_run:
        print(f"[DRY-RUN] Would write: {output_path}")
    else:
        with open(output_path, 'w') as f:
            json.dump(bedrock_metadata, f, indent=2)
        print(f"[OK] Wrote: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate Bedrock KB metadata files from scraper metadata")
    parser.add_argument(
        '--pdfs-dir',
        default='../scraped_content/raw/pdfs',
        help='Directory containing *_pdf.json files (default: ../scraped_content/raw/pdfs)'
    )
    parser.add_argument(
        '--output-dir',
        default='./bedrock_metadata',
        help='Output directory for .metadata.json files (default: ./bedrock_metadata)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without writing files'
    )
    args = parser.parse_args()

    # Resolve paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdfs_dir = os.path.join(script_dir, args.pdfs_dir) if not os.path.isabs(args.pdfs_dir) else args.pdfs_dir
    output_dir = os.path.join(script_dir, args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir

    print(f"Loading metadata from: {pdfs_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 60)

    # Load scraper metadata
    metadata_list = load_scraper_metadata(pdfs_dir)
    print(f"Found {len(metadata_list)} PDF metadata files")

    if not metadata_list:
        print("[ERROR] No metadata files found. Check --pdfs-dir path.")
        sys.exit(1)

    # Create output directory
    if not args.dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Generate Bedrock metadata files
    success_count = 0
    for metadata in metadata_list:
        bedrock_metadata = generate_bedrock_metadata(metadata)
        write_metadata_file(output_dir, metadata['filename'], bedrock_metadata, args.dry_run)
        success_count += 1

    print("-" * 60)
    print(f"Generated {success_count} Bedrock metadata files")

    if not args.dry_run:
        print(f"\nNext steps:")
        print(f"  1. Review files in {output_dir}")
        print(f"  2. Run: python upload_bedrock_metadata.py")


if __name__ == '__main__':
    main()
