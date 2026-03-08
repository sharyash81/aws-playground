import argparse
import subprocess
import shutil
from pathlib import Path

TABLES = [
    "customer",
    "lineitem",
    "nation",
    "orders",
    "part",
    "partsupp",
    "region",
    "supplier",
]


def run(cmd: list[str], cwd: str | None = None) -> None:
    subprocess.check_call(cmd, cwd=cwd)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_tool_binary(tool: str, explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Generator binary not found: {path}")
        return path

    root = _repo_root()
    if tool == "tpch-dbgen":
        candidates = [(root / "vendor" / "tpch-dbgen" / "dbgen").resolve()]
    else:
        candidates = [(root / "vendor" / "tpchgen-rs" / "target" / "release" / "tpchgen-cli").resolve()]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Generator binary not found. Checked: {', '.join(str(c) for c in candidates)}")


def _validate_outputs(out_dir: Path) -> None:
    missing = [t for t in TABLES if not (out_dir / f"{t}.tbl").exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated .tbl files: {missing}")


def _run_tpch_dbgen(binary: Path, scale_factor: str, out_dir: Path, chunks: int | None, chunk: int | None) -> None:
    repo_dir = binary.parent
    dists_src = repo_dir / "dists.dss"
    dists_dst = out_dir / "dists.dss"

    if not dists_src.exists():
        raise FileNotFoundError(f"dists.dss not found next to dbgen binary: {dists_src}")
    if not dists_dst.exists():
        shutil.copyfile(dists_src, dists_dst)

    cmd = [str(binary), "-s", str(scale_factor), "-f"]
    if chunks is not None or chunk is not None:
        if chunks is None or chunk is None:
            raise SystemExit("Both --chunks and --chunk must be set together")
        cmd += ["-C", str(chunks), "-S", str(chunk)]

    run(cmd, cwd=str(out_dir))


def _run_tpchgen_rs(binary: Path, scale_factor: str, out_dir: Path, chunks: int | None, chunk: int | None) -> None:
    cmd = [
        str(binary),
        "--scale-factor",
        str(scale_factor),
        "--output-dir",
        str(out_dir),
        "--format",
        "tbl",
    ]
    if chunks is not None or chunk is not None:
        if chunks is None or chunk is None:
            raise SystemExit("Both --chunks and --chunk must be set together")
        cmd += ["--parts", str(chunks), "--part", str(chunk + 1)]

    run(cmd)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tool", choices=["tpch-dbgen", "tpchgen-rs"], default="tpchgen-rs")
    p.add_argument("--generator-path", default=None)
    p.add_argument("--sf", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--chunks", type=int)
    p.add_argument("--chunk", type=int)
    args = p.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    generator = _resolve_tool_binary(args.tool, args.generator_path)

    if args.tool == "tpch-dbgen":
        _run_tpch_dbgen(generator, args.sf, out_dir, args.chunks, args.chunk)
    else:
        _run_tpchgen_rs(generator, args.sf, out_dir, args.chunks, args.chunk)

    _validate_outputs(out_dir)


if __name__ == "__main__":
    main()
