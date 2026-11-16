#!/usr/bin/env python3
"""Attach Hive Parquet with an in-memory DuckDB session. Never writes a .duckdb file.

The interchange store is Parquet. DuckDB/Polars/Spark open it at query time.
Persisting retrieval.duckdb duplicated the same bytes and is not allowed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import duckdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import add_root_arg, derived_dir, resolve_root  # noqa: E402


def db_path(root: str) -> str:
    """Legacy path. A file here is stale and should be deleted, not opened."""
    return os.path.join(derived_dir(root), "retrieval.duckdb")


def _parquet_glob(root: str, name: str) -> str | None:
    base = os.path.join(derived_dir(root), name)
    if not os.path.isdir(base):
        return None
    glob = os.path.join(base, "**", "*.parquet")
    for dp, _, fns in os.walk(base):
        if any(f.endswith(".parquet") for f in fns):
            return glob
    return None


def connect(root: str, read_only: bool = False):
    """In-memory DuckDB with VIEWs over Parquet. Does not create retrieval.duckdb."""
    root = resolve_root(root)
    stale = db_path(root)
    if not read_only and os.path.isfile(stale):
        os.remove(stale)
    chunks = _parquet_glob(root, "chunks")
    if not chunks:
        raise FileNotFoundError(
            f"missing chunks parquet under {os.path.join(derived_dir(root), 'chunks')}"
        )
    con = duckdb.connect(":memory:")
    chunk_sql = chunks.replace("'", "''")
    con.execute(
        "CREATE VIEW chunks AS SELECT * REPLACE (CAST(year AS VARCHAR) AS year) "
        f"FROM read_parquet('{chunk_sql}', hive_partitioning=true)"
    )
    msg = _parquet_glob(root, "messages")
    if msg:
        msg_sql = msg.replace("'", "''")
        con.execute(
            "CREATE VIEW messages AS SELECT * REPLACE (CAST(year AS VARCHAR) AS year) "
            f"FROM read_parquet('{msg_sql}', hive_partitioning=true)"
        )
    cases = os.path.join(derived_dir(root), "cases", "cases.parquet")
    if os.path.isfile(cases):
        c_sql = cases.replace("'", "''")
        con.execute(f"CREATE VIEW cases AS SELECT * FROM read_parquet('{c_sql}')")
    docs = os.path.join(derived_dir(root), "doc_chunks", "doc_chunks.parquet")
    if os.path.isfile(docs):
        d_sql = docs.replace("'", "''")
        con.execute(
            "CREATE VIEW documents AS SELECT * REPLACE (CAST(year AS VARCHAR) AS year) "
            f"FROM read_parquet('{d_sql}')"
        )
    summaries = os.path.join(derived_dir(root), "summaries")
    if os.path.isdir(summaries):
        files = []
        for dp, _, fns in os.walk(summaries):
            files.extend(os.path.join(dp, f) for f in fns if f.endswith(".parquet"))
        if files:
            quoted = ", ".join("'" + f.replace("'", "''") + "'" for f in files)
            con.execute(f"CREATE VIEW summaries AS SELECT * FROM read_parquet([{quoted}])")
    return con


def build_fts(root: str) -> dict:
    """Validate Parquet is queryable. Does not persist a DuckDB file."""
    root = resolve_root(root)
    stale = db_path(root)
    if os.path.isfile(stale):
        os.remove(stale)
    con = connect(root)
    n = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    n_msg = 0
    n_cases = 0
    n_sum = 0
    n_docs = 0
    try:
        n_msg = con.execute("SELECT count(*) FROM messages").fetchone()[0]
    except Exception:
        pass
    try:
        n_cases = con.execute("SELECT count(*) FROM cases").fetchone()[0]
    except Exception:
        pass
    try:
        n_sum = con.execute("SELECT count(*) FROM summaries").fetchone()[0]
    except Exception:
        pass
    try:
        n_docs = con.execute("SELECT count(*) FROM documents").fetchone()[0]
    except Exception:
        pass
    con.close()
    report = {
        "store": "parquet",
        "persist_duckdb": False,
        "chunks": n,
        "messages": n_msg,
        "cases": n_cases,
        "summaries": n_sum,
        "documents": n_docs,
        "vss": False,
        "note": "Query with in-memory DuckDB or Polars against Hive Parquet. "
                "Do not write retrieval.duckdb next to the corpus.",
    }
    with open(os.path.join(derived_dir(root), "fts_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    add_root_arg(ap)
    args = ap.parse_args()
    print(json.dumps(build_fts(args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
