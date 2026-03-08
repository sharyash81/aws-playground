#!/usr/bin/env python3
"""Invoke a single Lambda function via the AWS SDK and print the response."""

import argparse
import json
import sys
import boto3
from botocore.exceptions import ClientError


def invoke_lambda(
    function_name: str,
    payload: dict,
    invocation_type: str = "RequestResponse",
    region: str = "us-east-1",
) -> dict:
    client = boto3.client("lambda", region_name=region)

    print(f"[INFO] Invoking Lambda: {function_name}")
    print(f"[INFO] Invocation type: {invocation_type}")
    print(f"[INFO] Payload: {json.dumps(payload, indent=2)}")

    try:
        response = client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except ClientError as e:
        print(f"[ERROR] Invocation failed: {e}")
        sys.exit(1)

    status_code = response["StatusCode"]
    print(f"[INFO] HTTP status: {status_code}")

    if invocation_type == "Event":
        print("[OK] Async invocation accepted (no response body for Event type)")
        return {"statusCode": status_code}

    raw = response["Payload"].read()
    result = json.loads(raw)
    print(f"[OK] Response:\n{json.dumps(result, indent=2)}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Invoke an AWS Lambda function")
    parser.add_argument("function_name", help="Lambda function name or ARN")
    parser.add_argument(
        "--payload",
        help='JSON payload string (default: {"action":"hello"})',
        default='{"action":"hello"}',
    )
    parser.add_argument(
        "--type",
        choices=["RequestResponse", "Event", "DryRun"],
        default="RequestResponse",
        help="Invocation type (default: RequestResponse)",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON payload: {e}")
        sys.exit(1)

    invoke_lambda(args.function_name, payload, args.type, args.region)


if __name__ == "__main__":
    main()
