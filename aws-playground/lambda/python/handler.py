import json
import os
import boto3
from datetime import datetime

s3 = boto3.client("s3")
S3_BUCKET = os.environ.get("S3_BUCKET", "")


def lambda_handler(event, context):
    action = event.get("action", "hello")
    source = event.get("source", "unknown")

    if action == "hello":
        return _hello(source)
    elif action == "s3_write":
        return _s3_write(event)
    elif action == "s3_read":
        return _s3_read(event)
    else:
        return {"statusCode": 400, "body": json.dumps({"error": f"Unknown action: {action}"})}


def _hello(source):
    message = {
        "message": "Hello from Python Lambda!",
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
        "runtime": "python3.12",
    }
    return {"statusCode": 200, "body": json.dumps(message)}


def _s3_write(event):
    key = event.get("key", f"lambda-output/{datetime.utcnow().isoformat()}.txt")
    content = event.get("content", f"Written by Python Lambda at {datetime.utcnow().isoformat()}")
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=content.encode("utf-8"))
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Written to S3", "bucket": S3_BUCKET, "key": key}),
    }


def _s3_read(event):
    key = event.get("key")
    if not key:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing 'key' in event"})}
    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
    content = response["Body"].read().decode("utf-8")
    return {
        "statusCode": 200,
        "body": json.dumps({"bucket": S3_BUCKET, "key": key, "content": content}),
    }
