import argparse
import os
import subprocess
import shutil
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None) -> None:
    subprocess.check_call(cmd, cwd=cwd)


def build_tpch_dbgen(repo_dir: str) -> None:
    """Build traditional C-based tpch-dbgen"""
    os.makedirs(os.path.dirname(repo_dir), exist_ok=True)

    if not os.path.exists(repo_dir):
        run([
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/electrum/tpch-dbgen.git",
            repo_dir,
        ])

    makefile = os.path.join(repo_dir, "makefile")
    if not os.path.exists(makefile):
        raise FileNotFoundError(f"tpch-dbgen makefile not found at: {makefile}")

    run(["make"], cwd=repo_dir)

    dbgen = os.path.join(repo_dir, "dbgen")
    if not os.path.exists(dbgen):
        raise FileNotFoundError(f"dbgen binary not found at: {dbgen}")


def build_tpchgen_rs(repo_dir: str) -> None:
    """Build faster Rust-based tpchgen-rs"""
    os.makedirs(os.path.dirname(repo_dir), exist_ok=True)

    if not os.path.exists(repo_dir):
        run([
            "git",
            "clone",
            "--depth",
            "1",
            "https://github.com/clflushopt/tpchgen-rs.git",
            repo_dir,
        ])

    cargo_toml = os.path.join(repo_dir, "Cargo.toml")
    if not os.path.exists(cargo_toml):
        raise FileNotFoundError(f"tpchgen-rs Cargo.toml not found at: {cargo_toml}")

    run(["cargo", "build", "--release"], cwd=repo_dir)

    tpchgen_rs = os.path.join(repo_dir, "target", "release", "tpchgen-cli")
    if not os.path.exists(tpchgen_rs):
        raise FileNotFoundError(f"tpchgen-rs binary not found at: {tpchgen_rs}")


def prepare_lambda_bundle(repo_root: Path, c_repo_dir: str, rust_repo_dir: str) -> None:
    lambda_bin_dir = repo_root / "lambda" / "tpch_generator" / "bin"
    lambda_bin_dir.mkdir(parents=True, exist_ok=True)

    dbgen = Path(c_repo_dir) / "dbgen"
    dists = Path(c_repo_dir) / "dists.dss"
    tpchgen_cli = Path(rust_repo_dir) / "target" / "release" / "tpchgen-cli"

    if dbgen.exists():
        shutil.copy2(dbgen, lambda_bin_dir / "dbgen")
    if dists.exists():
        shutil.copy2(dists, lambda_bin_dir / "dists.dss")
    if tpchgen_cli.exists():
        shutil.copy2(tpchgen_cli, lambda_bin_dir / "tpchgen-cli")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_c_repo = repo_root / "vendor" / "tpch-dbgen"
    default_rust_repo = repo_root / "vendor" / "tpchgen-rs"
    p = argparse.ArgumentParser()
    p.add_argument("--tool", choices=["tpch-dbgen", "tpchgen-rs", "both"], default="both")
    p.add_argument("--c-repo-dir", default=str(default_c_repo))
    p.add_argument("--rust-repo-dir", default=str(default_rust_repo))
    p.add_argument("--prepare-lambda", action="store_true")
    args = p.parse_args()

    if args.tool in ["tpch-dbgen", "both"]:
        print("Building traditional tpch-dbgen...")
        build_tpch_dbgen(os.path.abspath(args.c_repo_dir))
        print("✅ tpch-dbgen built successfully")

    if args.tool in ["tpchgen-rs", "both"]:
        print("Building faster tpchgen-rs...")
        build_tpchgen_rs(os.path.abspath(args.rust_repo_dir))
        print("✅ tpchgen-rs built successfully")

    if args.prepare_lambda:
        prepare_lambda_bundle(repo_root, os.path.abspath(args.c_repo_dir), os.path.abspath(args.rust_repo_dir))
        print("✅ Copied generator binaries into lambda/tpch_generator/bin/")


if __name__ == "__main__":
    main()
