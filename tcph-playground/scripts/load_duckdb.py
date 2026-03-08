import argparse
import os
import re
from pathlib import Path
import duckdb


def _read_tpch_schema_ddl(ddl_path: str) -> list[str]:
    with open(ddl_path, "r", encoding="utf-8") as f:
        raw = f.read()

    lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
    text = "\n".join(lines)

    stmts = [s.strip() for s in text.split(";") if s.strip()]
    out: list[str] = []
    for s in stmts:
        if not re.match(r"^CREATE\s+TABLE\s+", s, re.IGNORECASE):
            continue

        s = re.sub(r"\bCHAR\s*\(\s*\d+\s*\)", "VARCHAR", s, flags=re.IGNORECASE)
        s = re.sub(r"\bVARCHAR\s*\(\s*\d+\s*\)", "VARCHAR", s, flags=re.IGNORECASE)
        out.append(s + ";")
    return out


def _table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    rows = con.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [(r[1], r[2]) for r in rows]


def _load_tbl(con: duckdb.DuckDBPyConnection, table: str, tbl_path: str) -> None:
    if not os.path.exists(tbl_path):
        raise FileNotFoundError(f"Table file not found: {tbl_path}")

    cols = _table_columns(con, table)
    select_cols = ", ".join(col_name for col_name, _ in cols)
    csv_columns = ", ".join(f"'{col_name}': '{col_type}'" for col_name, col_type in cols)
    # dbgen/tpchgen-rs lines end with a trailing delimiter, so we consume one extra dummy column.
    csv_columns_with_dummy = f"{csv_columns}, '_end': 'VARCHAR'"

    con.execute(
        f"""
        INSERT INTO {table}
        SELECT {select_cols}
        FROM read_csv(
            '{tbl_path}',
            delim='|',
            header=false,
            auto_detect=false,
            columns={{ {csv_columns_with_dummy} }}
        )
        """
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_ddl = repo_root / "vendor" / "tpch-dbgen" / "dss.ddl"
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--ddl", default=str(default_ddl))
    p.add_argument("--tables", nargs="*", default=None)
    p.add_argument("--create-indexes", action="store_true")
    args = p.parse_args()

    db_path = os.path.abspath(args.db)
    data_dir = os.path.abspath(args.data)
    ddl_path = os.path.abspath(args.ddl)

    if args.tables:
        tables = args.tables
    else:
        tables = [t for t in os.listdir(data_dir) if t.endswith(".tbl")]
        tables = [os.path.splitext(t)[0] for t in tables]

    con = duckdb.connect(db_path)

    if not os.path.exists(ddl_path):
        raise FileNotFoundError(f"dss.ddl not found (expected from tpch-dbgen): {ddl_path}")

    for stmt in _read_tpch_schema_ddl(ddl_path):
        con.execute(stmt)

    existing = {r[0].lower() for r in con.execute("SHOW TABLES").fetchall()}
    for t in tables:
        if t not in existing:
            continue
        actual_table = next(r[0] for r in con.execute("SHOW TABLES").fetchall() if r[0].lower() == t)
        _load_tbl(con, actual_table, os.path.join(data_dir, f"{t}.tbl"))

    if args.create_indexes:
        if "lineitem" in existing:
            cols = {c[0] for c in _table_columns(con, "lineitem")}
            if "l_orderkey" in cols:
                con.execute("CREATE INDEX IF NOT EXISTS idx_lineitem_orderkey ON lineitem(l_orderkey)")
        if "orders" in existing:
            cols = {c[0] for c in _table_columns(con, "orders")}
            if "o_custkey" in cols:
                con.execute("CREATE INDEX IF NOT EXISTS idx_orders_custkey ON orders(o_custkey)")

    con.close()


if __name__ == "__main__":
    main()
