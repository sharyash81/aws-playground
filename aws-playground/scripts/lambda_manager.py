#!/usr/bin/env python3
"""
Lambda Function Manager
=======================
Invoke hundreds of Lambda functions concurrently, distribute tasks across them,
and wait for all completions with a live progress display.

Usage examples:
  # Invoke the same function 200 times with different payloads
  python3 lambda_manager.py fan-out \
      --function my-function \
      --count 200 \
      --payload '{"action":"hello"}' \
      --concurrency 50

  # Distribute a list of tasks (from a JSON file) across a function
  python3 lambda_manager.py distribute \
      --function my-function \
      --tasks tasks.json \
      --concurrency 50

  # Invoke multiple different functions each once
  python3 lambda_manager.py multi \
      --functions fn-a fn-b fn-c \
      --payload '{"action":"hello"}'
"""

import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class InvocationTask:
    task_id: int
    function_name: str
    payload: dict


@dataclass
class InvocationResult:
    task_id: int
    function_name: str
    success: bool
    status_code: int = 0
    response: Any = None
    error: str = ""
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Core invocation
# ---------------------------------------------------------------------------

def _invoke_one(client: boto3.client, task: InvocationTask) -> InvocationResult:
    start = time.monotonic()
    try:
        resp = client.invoke(
            FunctionName=task.function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(task.payload).encode("utf-8"),
        )
        duration_ms = (time.monotonic() - start) * 1000
        raw = resp["Payload"].read()
        body = json.loads(raw) if raw else {}
        return InvocationResult(
            task_id=task.task_id,
            function_name=task.function_name,
            success=resp["StatusCode"] in (200, 202),
            status_code=resp["StatusCode"],
            response=body,
            duration_ms=duration_ms,
        )
    except ClientError as e:
        duration_ms = (time.monotonic() - start) * 1000
        return InvocationResult(
            task_id=task.task_id,
            function_name=task.function_name,
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = (time.monotonic() - start) * 1000
        return InvocationResult(
            task_id=task.task_id,
            function_name=task.function_name,
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


# ---------------------------------------------------------------------------
# Progress tracker
# ---------------------------------------------------------------------------

class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.done = 0
        self.succeeded = 0
        self.failed = 0
        self._lock = threading.Lock()
        self._start = time.monotonic()

    def record(self, result: InvocationResult):
        with self._lock:
            self.done += 1
            if result.success:
                self.succeeded += 1
            else:
                self.failed += 1
            self._print()

    def _print(self):
        elapsed = time.monotonic() - self._start
        pct = (self.done / self.total) * 100
        bar_len = 40
        filled = int(bar_len * self.done / self.total)
        bar = "█" * filled + "░" * (bar_len - filled)
        rps = self.done / elapsed if elapsed > 0 else 0
        print(
            f"\r  [{bar}] {self.done}/{self.total} ({pct:.0f}%)  "
            f"✓{self.succeeded} ✗{self.failed}  {rps:.1f} inv/s  {elapsed:.1f}s",
            end="",
            flush=True,
        )

    def finish(self):
        elapsed = time.monotonic() - self._start
        print()
        print(f"\n{'='*60}")
        print(f"  Total:     {self.total}")
        print(f"  Succeeded: {self.succeeded}")
        print(f"  Failed:    {self.failed}")
        print(f"  Elapsed:   {elapsed:.2f}s")
        print(f"  Avg rate:  {self.total / elapsed:.1f} inv/s")
        print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class LambdaManager:
    def __init__(self, region: str = "us-east-1", concurrency: int = 50):
        self.region = region
        self.concurrency = concurrency
        self._client = boto3.client("lambda", region_name=region)

    def run(self, tasks: list[InvocationTask], output_file: str | None = None) -> list[InvocationResult]:
        total = len(tasks)
        print(f"\n[INFO] Dispatching {total} invocations | concurrency={self.concurrency} | region={self.region}")
        print(f"[INFO] Started at {datetime.utcnow().isoformat()}Z\n")

        tracker = ProgressTracker(total)
        results: list[InvocationResult] = []

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {pool.submit(_invoke_one, self._client, task): task for task in tasks}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                tracker.record(result)

        tracker.finish()

        if output_file:
            self._save_results(results, output_file)

        return results

    def _save_results(self, results: list[InvocationResult], path: str):
        data = [
            {
                "task_id": r.task_id,
                "function_name": r.function_name,
                "success": r.success,
                "status_code": r.status_code,
                "duration_ms": round(r.duration_ms, 2),
                "response": r.response,
                "error": r.error,
            }
            for r in sorted(results, key=lambda x: x.task_id)
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[INFO] Results saved to: {path}")

    # ------------------------------------------------------------------
    # High-level modes
    # ------------------------------------------------------------------

    def fan_out(self, function_name: str, count: int, base_payload: dict) -> list[InvocationResult]:
        """Invoke the same function `count` times, each with task_id injected."""
        tasks = [
            InvocationTask(
                task_id=i,
                function_name=function_name,
                payload={**base_payload, "task_id": i},
            )
            for i in range(count)
        ]
        return self.run(tasks)

    def distribute(self, function_name: str, task_payloads: list[dict]) -> list[InvocationResult]:
        """Distribute a list of distinct task payloads across the same function."""
        tasks = [
            InvocationTask(task_id=i, function_name=function_name, payload=p)
            for i, p in enumerate(task_payloads)
        ]
        return self.run(tasks)

    def multi_function(self, function_names: list[str], base_payload: dict) -> list[InvocationResult]:
        """Invoke each function in the list once."""
        tasks = [
            InvocationTask(task_id=i, function_name=fn, payload={**base_payload, "task_id": i})
            for i, fn in enumerate(function_names)
        ]
        return self.run(tasks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_fan_out(args):
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON payload: {e}")
        sys.exit(1)

    mgr = LambdaManager(region=args.region, concurrency=args.concurrency)
    results = mgr.fan_out(args.function, args.count, payload)

    if args.output:
        mgr._save_results(results, args.output)

    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n[WARN] {len(failed)} invocation(s) failed. First error: {failed[0].error}")
        sys.exit(1)


def cmd_distribute(args):
    if not os.path.exists(args.tasks):
        print(f"[ERROR] Tasks file not found: {args.tasks}")
        sys.exit(1)

    with open(args.tasks) as f:
        task_payloads = json.load(f)

    if not isinstance(task_payloads, list):
        print("[ERROR] Tasks file must contain a JSON array of payload objects")
        sys.exit(1)

    mgr = LambdaManager(region=args.region, concurrency=args.concurrency)
    results = mgr.distribute(args.function, task_payloads)

    if args.output:
        mgr._save_results(results, args.output)

    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n[WARN] {len(failed)} invocation(s) failed. First error: {failed[0].error}")
        sys.exit(1)


def cmd_multi(args):
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON payload: {e}")
        sys.exit(1)

    mgr = LambdaManager(region=args.region, concurrency=args.concurrency)
    results = mgr.multi_function(args.functions, payload)

    if args.output:
        mgr._save_results(results, args.output)

    failed = [r for r in results if not r.success]
    if failed:
        print(f"\n[WARN] {len(failed)} invocation(s) failed. First error: {failed[0].error}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Lambda Function Manager — invoke 100s of Lambdas concurrently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--concurrency", type=int, default=50, help="Max parallel invocations (default: 50)")
    parser.add_argument("--output", help="Save results to this JSON file", default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    # fan-out: same function, N times
    p_fan = sub.add_parser("fan-out", help="Invoke one function N times with different task_ids")
    p_fan.add_argument("--function", required=True, help="Lambda function name or ARN")
    p_fan.add_argument("--count", type=int, required=True, help="Number of invocations")
    p_fan.add_argument("--payload", default='{"action":"hello"}', help="Base JSON payload")
    p_fan.set_defaults(func=cmd_fan_out)

    # distribute: same function, list of distinct payloads from file
    p_dist = sub.add_parser("distribute", help="Distribute a list of task payloads across one function")
    p_dist.add_argument("--function", required=True, help="Lambda function name or ARN")
    p_dist.add_argument("--tasks", required=True, help="Path to JSON file containing array of payloads")
    p_dist.set_defaults(func=cmd_distribute)

    # multi: different functions, each invoked once
    p_multi = sub.add_parser("multi", help="Invoke multiple different functions each once")
    p_multi.add_argument("--functions", nargs="+", required=True, help="List of Lambda function names")
    p_multi.add_argument("--payload", default='{"action":"hello"}', help="Base JSON payload")
    p_multi.set_defaults(func=cmd_multi)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
