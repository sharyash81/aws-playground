#!/usr/bin/env python3
"""Upload a file to S3 (standard single-part upload)."""

import argparse
import os
import sys
import boto3
from botocore.exceptions import ClientError


def upload_file(local_path: str, bucket: str, s3_key: str | None = None) -> None:
    if not os.path.exists(local_path):
        print(f"[ERROR] File not found: {local_path}")
        sys.exit(1)

    if s3_key is None:
        s3_key = os.path.basename(local_path)

    s3 = boto3.client("s3")
    file_size = os.path.getsize(local_path)
    print(f"[INFO] Uploading '{local_path}' ({file_size:,} bytes) -> s3://{bucket}/{s3_key}")

    try:
        s3.upload_file(local_path, bucket, s3_key)
        print(f"[OK] Upload complete: s3://{bucket}/{s3_key}")
    except ClientError as e:
        print(f"[ERROR] Upload failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Upload a file to S3")
    parser.add_argument("local_path", help="Local file path to upload")
    parser.add_argument("bucket", help="S3 bucket name")
    parser.add_argument("--key", help="S3 object key (default: filename)", default=None)
    args = parser.parse_args()

    upload_file(args.local_path, args.bucket, args.key)


if __name__ == "__main__":
    main()
