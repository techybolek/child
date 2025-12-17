#!/usr/bin/env python3
"""
Upload Bedrock KB metadata files to S3 and trigger Knowledge Base resync.

Uploads: bedrock_metadata/*.metadata.json -> s3://cohort-tx-1/
Resyncs: Knowledge Base 371M2G58TV via start_ingestion_job()

Prerequisites:
    1. Run generate_bedrock_metadata.py first
    2. AWS credentials configured (aws configure or environment variables)

Usage:
    python upload_bedrock_metadata.py
    python upload_bedrock_metadata.py --metadata-dir ./custom_dir
    python upload_bedrock_metadata.py --dry-run
    python upload_bedrock_metadata.py --skip-resync
"""

import argparse
import glob
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

# Bedrock KB configuration
S3_BUCKET = 'cohort-tx-1'
KNOWLEDGE_BASE_ID = '371M2G58TV'
DATA_SOURCE_ID = 'V4C2EUGYSY'
AWS_REGION = 'us-east-1'


def upload_metadata_to_s3(s3_client, metadata_dir: str, bucket: str, dry_run: bool = False) -> int:
    """Upload all .metadata.json files to S3 bucket.

    Args:
        s3_client: Boto3 S3 client
        metadata_dir: Directory containing .metadata.json files
        bucket: S3 bucket name
        dry_run: If True, don't upload files

    Returns:
        Number of files uploaded
    """
    metadata_files = glob.glob(os.path.join(metadata_dir, "*.metadata.json"))

    if not metadata_files:
        print(f"[ERROR] No .metadata.json files found in {metadata_dir}")
        return 0

    print(f"Found {len(metadata_files)} metadata files to upload")
    uploaded = 0

    for file_path in sorted(metadata_files):
        filename = os.path.basename(file_path)
        s3_key = filename  # Upload to bucket root (same level as PDFs)

        if dry_run:
            print(f"[DRY-RUN] Would upload: {filename} -> s3://{bucket}/{s3_key}")
        else:
            try:
                s3_client.upload_file(file_path, bucket, s3_key)
                print(f"[OK] Uploaded: {filename} -> s3://{bucket}/{s3_key}")
                uploaded += 1
            except ClientError as e:
                print(f"[ERROR] Failed to upload {filename}: {e}")

    return uploaded


def start_kb_resync(bedrock_client, kb_id: str, ds_id: str, dry_run: bool = False) -> str | None:
    """Trigger Knowledge Base ingestion job to resync data source.

    Args:
        bedrock_client: Boto3 bedrock-agent client
        kb_id: Knowledge Base ID
        ds_id: Data Source ID
        dry_run: If True, don't trigger resync

    Returns:
        Ingestion job ID or None if dry run
    """
    if dry_run:
        print(f"[DRY-RUN] Would trigger resync for KB {kb_id}, DS {ds_id}")
        return None

    try:
        response = bedrock_client.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )
        job_id = response['ingestionJob']['ingestionJobId']
        status = response['ingestionJob']['status']
        print(f"[OK] Started ingestion job: {job_id} (status: {status})")
        return job_id
    except ClientError as e:
        print(f"[ERROR] Failed to start ingestion job: {e}")
        return None


def wait_for_ingestion(bedrock_client, kb_id: str, ds_id: str, job_id: str, timeout: int = 300) -> bool:
    """Wait for ingestion job to complete.

    Args:
        bedrock_client: Boto3 bedrock-agent client
        kb_id: Knowledge Base ID
        ds_id: Data Source ID
        job_id: Ingestion job ID
        timeout: Max seconds to wait

    Returns:
        True if completed successfully, False otherwise
    """
    print(f"Waiting for ingestion job {job_id} to complete (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = bedrock_client.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id,
                ingestionJobId=job_id
            )
            status = response['ingestionJob']['status']

            if status == 'COMPLETE':
                stats = response['ingestionJob'].get('statistics', {})
                print(f"[OK] Ingestion complete!")
                print(f"     Scanned: {stats.get('numberOfDocumentsScanned', 'N/A')}")
                print(f"     Indexed: {stats.get('numberOfNewDocumentsIndexed', 'N/A')}")
                print(f"     Modified: {stats.get('numberOfModifiedDocumentsIndexed', 'N/A')}")
                print(f"     Deleted: {stats.get('numberOfDocumentsDeleted', 'N/A')}")
                print(f"     Failed: {stats.get('numberOfDocumentsFailed', 'N/A')}")
                return True
            elif status == 'FAILED':
                failure_reasons = response['ingestionJob'].get('failureReasons', [])
                print(f"[ERROR] Ingestion failed: {failure_reasons}")
                return False
            else:
                print(f"  Status: {status}...")
                time.sleep(10)

        except ClientError as e:
            print(f"[ERROR] Failed to check ingestion status: {e}")
            return False

    print(f"[ERROR] Timeout waiting for ingestion to complete")
    return False


def main():
    parser = argparse.ArgumentParser(description="Upload Bedrock KB metadata to S3 and resync")
    parser.add_argument(
        '--metadata-dir',
        default='./bedrock_metadata',
        help='Directory containing .metadata.json files (default: ./bedrock_metadata)'
    )
    parser.add_argument(
        '--bucket',
        default=S3_BUCKET,
        help=f'S3 bucket name (default: {S3_BUCKET})'
    )
    parser.add_argument(
        '--kb-id',
        default=KNOWLEDGE_BASE_ID,
        help=f'Knowledge Base ID (default: {KNOWLEDGE_BASE_ID})'
    )
    parser.add_argument(
        '--ds-id',
        default=DATA_SOURCE_ID,
        help=f'Data Source ID (default: {DATA_SOURCE_ID})'
    )
    parser.add_argument(
        '--region',
        default=AWS_REGION,
        help=f'AWS region (default: {AWS_REGION})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without uploading or resyncing'
    )
    parser.add_argument(
        '--skip-resync',
        action='store_true',
        help='Upload files only, skip Knowledge Base resync'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Start resync but don\'t wait for completion'
    )
    args = parser.parse_args()

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    metadata_dir = os.path.join(script_dir, args.metadata_dir) if not os.path.isabs(args.metadata_dir) else args.metadata_dir

    print(f"Metadata directory: {metadata_dir}")
    print(f"S3 bucket: {args.bucket}")
    print(f"Knowledge Base ID: {args.kb_id}")
    print(f"Data Source ID: {args.ds_id}")
    print(f"Region: {args.region}")
    print(f"Dry run: {args.dry_run}")
    print(f"Skip resync: {args.skip_resync}")
    print("-" * 60)

    # Verify metadata directory exists
    if not os.path.isdir(metadata_dir):
        print(f"[ERROR] Metadata directory not found: {metadata_dir}")
        print("Run generate_bedrock_metadata.py first")
        sys.exit(1)

    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=args.region)
    bedrock_client = boto3.client('bedrock-agent', region_name=args.region)

    # Step 1: Upload metadata files to S3
    print("\n[Step 1] Uploading metadata files to S3...")
    uploaded = upload_metadata_to_s3(s3_client, metadata_dir, args.bucket, args.dry_run)

    if uploaded == 0 and not args.dry_run:
        print("[ERROR] No files uploaded. Check AWS credentials and bucket permissions.")
        sys.exit(1)

    # Step 2: Trigger KB resync
    if args.skip_resync:
        print("\n[Step 2] Skipping Knowledge Base resync (--skip-resync)")
    else:
        print("\n[Step 2] Triggering Knowledge Base resync...")
        job_id = start_kb_resync(bedrock_client, args.kb_id, args.ds_id, args.dry_run)

        if job_id and not args.no_wait:
            print("\n[Step 3] Waiting for ingestion to complete...")
            success = wait_for_ingestion(bedrock_client, args.kb_id, args.ds_id, job_id)
            if not success:
                sys.exit(1)
        elif job_id:
            print("\n[Step 3] Skipping wait (--no-wait). Check status in AWS Console.")

    print("-" * 60)
    print("Done!")
    if not args.dry_run:
        print("\nTo verify, run:")
        print("  python -m evaluation.run_evaluation --mode bedrock --test --limit 1 --debug")


if __name__ == '__main__':
    main()
