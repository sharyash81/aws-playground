# TPC-H Playground

Configurable TPC-H workflows for:
- local generation + DuckDB query execution
- AWS Lambda generation + S3 storage + Athena queries
- both `tpch-dbgen` (C) and `tpchgen-rs` (Rust)

## Design Principles

- Single source of truth in `Makefile` variables (`SF`, `CHUNK`, `TOTAL_CHUNKS`, `S3_PREFIX`, `GEN_TOOL`)
- No synthetic fallback data in Lambda (fail fast if generators are missing)
- Athena table DDL uses placeholders and supports all 8 base TPC-H tables
- S3 layout isolates tables by path to avoid schema collisions:
  - `s3://<bucket>/<prefix>/sf<sf>/chunk<chunk>/<table>/<table>.tbl`

## Prerequisites

- Python 3.10+
- AWS CLI configured
- Terraform
- `make`

## Local Workflow

```bash
make submodules-init
make local-setup
make build-tools
make local-all SF=1 GEN_TOOL=tpchgen-rs
```

Outputs:
- data: `data/sf1_<tool>/`
- DuckDB: `tpch_sf1_<tool>.duckdb`
- query results: `results/sf1_<tool>/`

## Generator Speed Benchmark (Only)

This benchmark compares **data generation only** (not query runtime).

```bash
make local-benchmark SF=1
```

Output report:
- `results/benchmarks/sf1_generator_benchmark.json`

## AWS Workflow

1) Build tools and prepare Lambda binaries:

```bash
make submodules-init
make local-setup
make build-tools
```

Vendor tool sources are managed as Git submodules (`vendor/tpch-dbgen`, `vendor/tpchgen-rs`).
If you clone without `--recurse-submodules`, run `make submodules-init` before building.

2) Deploy AWS resources:

```bash
make init
make deploy
```

3) Run end-to-end pipeline:

```bash
make pipeline SF=1 CHUNK=0 TOTAL_CHUNKS=1 GEN_TOOL=tpchgen-rs
```

Pipeline steps:
- invoke Lambda to generate/upload TPC-H data
- create Athena external tables from `queries/athena_ddl.sql`
- execute a smoke query (`COUNT(*)` on `customer`)

## Key Files

- `scripts/gen_tpch_data.py`: local data generation for both tools
- `scripts/load_duckdb.py`: load `.tbl` data into DuckDB
- `scripts/run_queries.py`: run TPC-H queries locally
- `scripts/athena_runner.py`: create Athena tables and run Athena queries
- `lambda/tpch_generator/lambda_function.py`: Lambda entrypoint
- `queries/athena_ddl.sql`: Athena table definitions (templated)
