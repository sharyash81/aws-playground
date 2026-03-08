import argparse
import json
import subprocess
import time
from pathlib import Path


def run_generation(repo_root: Path, tool: str, sf: str, out_dir: Path) -> float:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        str(repo_root / "scripts" / "gen_tpch_data.py"),
        "--tool",
        tool,
        "--sf",
        sf,
        "--out",
        str(out_dir),
    ]
    start = time.perf_counter()
    subprocess.check_call(cmd, cwd=str(repo_root))
    return time.perf_counter() - start


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sf", default="1")
    p.add_argument("--out", required=True, help="Output benchmark JSON file")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    benchmark_dir = repo_root / "data" / f"benchmark_sf{args.sf}"
    dbgen_dir = benchmark_dir / "tpch-dbgen"
    rs_dir = benchmark_dir / "tpchgen-rs"

    # Keep benchmark runs independent and reproducible.
    if dbgen_dir.exists():
        subprocess.check_call(["rm", "-rf", str(dbgen_dir)])
    if rs_dir.exists():
        subprocess.check_call(["rm", "-rf", str(rs_dir)])

    dbgen_seconds = run_generation(repo_root, "tpch-dbgen", args.sf, dbgen_dir)
    rs_seconds = run_generation(repo_root, "tpchgen-rs", args.sf, rs_dir)

    speedup = (dbgen_seconds / rs_seconds) if rs_seconds > 0 else None
    summary = {
        "scale_factor": args.sf,
        "metric": "generation_seconds_only",
        "timings": {
            "tpch-dbgen": dbgen_seconds,
            "tpchgen-rs": rs_seconds,
        },
        "speedup_tpchgen_rs_over_tpch_dbgen": speedup,
        "outputs": {
            "tpch-dbgen": str(dbgen_dir),
            "tpchgen-rs": str(rs_dir),
        },
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    if speedup is None:
        print("tpch-dbgen: {:.3f}s, tpchgen-rs: {:.3f}s, speedup=n/a".format(dbgen_seconds, rs_seconds))
    else:
        print(
            "tpch-dbgen: {:.3f}s, tpchgen-rs: {:.3f}s, speedup(tpchgen-rs)={:.3f}x".format(
                dbgen_seconds, rs_seconds, speedup
            )
        )
    print(f"Wrote generator benchmark: {out_path}")


if __name__ == "__main__":
    main()
