#!/usr/bin/env python3
"""Download a file from S3 (standard single-part download)."""

import argparse
import os
import sys
import boto3
from botocore.exceptions import ClientError


def download_file(bucket: str, s3_key: str, local_path: str | None = None) -> None:
    if local_path is None:
        local_path = os.path.basename(s3_key)

    os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)

    s3 = boto3.client("s3")
    print(f"[INFO] Downloading s3://{bucket}/{s3_key} -> '{local_path}'")

    try:
        s3.download_file(bucket, s3_key, local_path)
        size = os.path.getsize(local_path)
        print(f"[OK] Download complete: '{local_path}' ({size:,} bytes)")
    except ClientError as e:
        print(f"[ERROR] Download failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download a file from S3")
    parser.add_argument("bucket", help="S3 bucket name")
    parser.add_argument("key", help="S3 object key")
    parser.add_argument("--output", help="Local output path (default: key basename)", default=None)
    args = parser.parse_args()

    download_file(args.bucket, args.key, args.output)


if __name__ == "__main__":
    main()
