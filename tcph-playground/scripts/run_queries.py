import argparse
import os
import time
import json
import csv

import duckdb


def split_queries(sql_text: str) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- name:"):
            if current_name is not None and "".join(current_lines).strip():
                queries.append((current_name, "\n".join(current_lines).strip().rstrip(";")))
            current_name = stripped.split(":", 1)[1].strip()
            current_lines = []
            continue
        if stripped.startswith("--") and current_name is None:
            continue
        if current_name is not None:
            current_lines.append(line)

    if current_name is not None and "".join(current_lines).strip():
        queries.append((current_name, "\n".join(current_lines).strip().rstrip(";")))

    return queries


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--queries", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    db_path = os.path.abspath(args.db)
    queries_path = os.path.abspath(args.queries)
    out_dir = os.path.abspath(args.out)

    os.makedirs(out_dir, exist_ok=True)

    with open(queries_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    queries = split_queries(sql_text)
    if not queries:
        raise SystemExit("No queries found in queries file")

    con = duckdb.connect(db_path, read_only=True)
    timings: dict[str, float] = {}

    for name, sql in queries:
        t0 = time.perf_counter()
        cur = con.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in (cur.description or [])]
        elapsed = time.perf_counter() - t0
        timings[name] = elapsed

        out_csv = os.path.join(out_dir, f"{name}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if cols:
                w.writerow(cols)
            w.writerows(rows)

    with open(os.path.join(out_dir, "timings.json"), "w", encoding="utf-8") as f:
        json.dump(timings, f, indent=2, sort_keys=True)

    con.close()


if __name__ == "__main__":
    main()
