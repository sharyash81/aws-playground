#!/usr/bin/env python3
"""
Multipart upload and download for S3.

Multipart upload splits large files into chunks and uploads them in parallel.
Multipart download uses byte-range requests to download chunks in parallel.
"""

import argparse
import os
import sys
import threading
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError


MULTIPART_THRESHOLD = 8 * 1024 * 1024   # 8 MB
MULTIPART_CHUNKSIZE = 8 * 1024 * 1024   # 8 MB
MAX_CONCURRENCY = 10


def _transfer_config() -> TransferConfig:
    return TransferConfig(
        multipart_threshold=MULTIPART_THRESHOLD,
        multipart_chunksize=MULTIPART_CHUNKSIZE,
        max_concurrency=MAX_CONCURRENCY,
        use_threads=True,
    )


class ProgressBar:
    def __init__(self, filename: str, total: int):
        self._filename = filename
        self._total = total
        self._seen = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount: int):
        with self._lock:
            self._seen += bytes_amount
            pct = (self._seen / self._total) * 100 if self._total else 0
            bar = "#" * int(pct // 2)
            print(f"\r  [{bar:<50}] {pct:5.1f}%  {self._seen:,}/{self._total:,} bytes", end="", flush=True)
            if self._seen >= self._total:
                print()


def multipart_upload(local_path: str, bucket: str, s3_key: str | None = None) -> None:
    if not os.path.exists(local_path):
        print(f"[ERROR] File not found: {local_path}")
        sys.exit(1)

    if s3_key is None:
        s3_key = os.path.basename(local_path)

    file_size = os.path.getsize(local_path)
    s3 = boto3.client("s3")
    config = _transfer_config()

    print(f"[INFO] Multipart upload: '{local_path}' ({file_size:,} bytes) -> s3://{bucket}/{s3_key}")
    print(f"[INFO] Chunk size: {MULTIPART_CHUNKSIZE // 1024 // 1024} MB | Concurrency: {MAX_CONCURRENCY}")

    try:
        s3.upload_file(
            local_path,
            bucket,
            s3_key,
            Config=config,
            Callback=ProgressBar(local_path, file_size),
        )
        print(f"[OK] Multipart upload complete: s3://{bucket}/{s3_key}")
    except ClientError as e:
        print(f"\n[ERROR] Upload failed: {e}")
        sys.exit(1)


def multipart_download(bucket: str, s3_key: str, local_path: str | None = None) -> None:
    if local_path is None:
        local_path = os.path.basename(s3_key)

    os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)

    s3 = boto3.client("s3")
    config = _transfer_config()

    try:
        head = s3.head_object(Bucket=bucket, Key=s3_key)
        file_size = head["ContentLength"]
    except ClientError as e:
        print(f"[ERROR] Cannot stat object: {e}")
        sys.exit(1)

    print(f"[INFO] Multipart download: s3://{bucket}/{s3_key} ({file_size:,} bytes) -> '{local_path}'")
    print(f"[INFO] Chunk size: {MULTIPART_CHUNKSIZE // 1024 // 1024} MB | Concurrency: {MAX_CONCURRENCY}")

    try:
        s3.download_file(
            bucket,
            s3_key,
            local_path,
            Config=config,
            Callback=ProgressBar(s3_key, file_size),
        )
        print(f"[OK] Multipart download complete: '{local_path}'")
    except ClientError as e:
        print(f"\n[ERROR] Download failed: {e}")
        sys.exit(1)


def generate_test_file(path: str, size_mb: int = 20) -> None:
    """Generate a dummy file for testing multipart upload."""
    size_bytes = size_mb * 1024 * 1024
    print(f"[INFO] Generating test file: '{path}' ({size_mb} MB)")
    with open(path, "wb") as f:
        f.write(os.urandom(size_bytes))
    print(f"[OK] Test file ready: '{path}'")


def main():
    parser = argparse.ArgumentParser(description="S3 multipart upload/download")
    sub = parser.add_subparsers(dest="command", required=True)

    up = sub.add_parser("upload", help="Multipart upload a file to S3")
    up.add_argument("local_path", help="Local file to upload")
    up.add_argument("bucket", help="S3 bucket name")
    up.add_argument("--key", help="S3 object key", default=None)

    dl = sub.add_parser("download", help="Multipart download a file from S3")
    dl.add_argument("bucket", help="S3 bucket name")
    dl.add_argument("key", help="S3 object key")
    dl.add_argument("--output", help="Local output path", default=None)

    gen = sub.add_parser("generate", help="Generate a test file for multipart upload testing")
    gen.add_argument("path", help="Output file path")
    gen.add_argument("--size-mb", type=int, default=20, help="File size in MB (default: 20)")

    args = parser.parse_args()

    if args.command == "upload":
        multipart_upload(args.local_path, args.bucket, args.key)
    elif args.command == "download":
        multipart_download(args.bucket, args.key, args.output)
    elif args.command == "generate":
        generate_test_file(args.path, args.size_mb)


if __name__ == "__main__":
    main()
