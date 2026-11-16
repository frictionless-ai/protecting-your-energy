#!/usr/bin/env python3
"""Parameterized read-only SQL over Hive Parquet (in-memory DuckDB, no .duckdb file)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_fts import connect  # noqa: E402
from common import add_root_arg, resolve_root  # noqa: E402

WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|COPY|ATTACH|CREATE|REPLACE|"
    r"EXPORT|IMPORT|CALL|PRAGMA|INSTALL|LOAD|VACUUM|CHECKPOINT)\b",
    re.I,
)


class FtsMissing(RuntimeError):
    pass

_CACHED_CON: dict[str, object] = {}


def connect_cached(root: str):
    """Reuse one in-memory DuckDB per process/root. Views attach Parquet at query time."""
    root = resolve_root(root)
    con = _CACHED_CON.get(root)
    if con is not None:
        return con
    con = connect(root, read_only=True)
    try:
        con.execute("SET threads TO 2")
        con.execute("SET memory_limit = '512MB'")
    except Exception:
        pass
    _CACHED_CON[root] = con
    return con


def assert_readonly_sql(sql: str) -> str:
    stripped = sql.strip()
    if not stripped:
        raise ValueError("empty query")
    if ";" in stripped.rstrip(";"):
        raise ValueError("multiple statements are not allowed")
    if ".." in stripped:
        raise ValueError("path traversal is not allowed")
    if WRITE_RE.search(stripped):
        raise ValueError("only SELECT / WITH queries are allowed")
    head = stripped.lstrip("(").split(None, 1)[0].upper()
    if head not in {"SELECT", "WITH"}:
        raise ValueError("only SELECT / WITH queries are allowed")
    return stripped.rstrip(";")


def query(
    root: str,
    sql: str | None = None,
    *,
    text: str | None = None,
    platform: str | None = None,
    year: str | None = None,
    author: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
    limit: int = 20,
    params: list | None = None,
    reuse: bool = False,
) -> list[dict]:
    root = resolve_root(root)
    try:
        con = connect_cached(root) if reuse else connect(root, read_only=True)
    except FileNotFoundError as e:
        raise FtsMissing(
            f"{e} — run tooling/retrieval/derive_parquet.py --root <root>"
        ) from e
    try:
        if sql:
            safe = assert_readonly_sql(sql)
            if not re.search(r"\bLIMIT\b", safe, re.I):
                safe = f"{safe} LIMIT {int(limit or 20)}"
            cur = con.execute(safe, params or [])
        else:
            clauses = ["1=1"]
            qparams: list = []
            if platform:
                clauses.append("platform = ?")
                qparams.append(platform)
            if year:
                clauses.append("CAST(year AS VARCHAR) = ?")
                qparams.append(str(year))
            if start_ts:
                clauses.append("start_ts >= ?")
                qparams.append(start_ts)
            if end_ts:
                clauses.append("end_ts <= ?")
                qparams.append(end_ts)
            if author:
                clauses.append("text ILIKE ?")
                qparams.append(f"%{author}%")
            where = " AND ".join(clauses)
            if text:
                sql = (
                    f"SELECT chunk_id, conversation_id, platform, year, start_ts, end_ts, "
                    f"substr(text, 1, 500) AS text "
                    f"FROM chunks WHERE {where} AND text ILIKE ? "
                    f"LIMIT {int(limit)}"
                )
                needle = f"%{text}%"
                cur = con.execute(sql, [*qparams, needle])
            else:
                sql = (
                    f"SELECT chunk_id, conversation_id, platform, year, start_ts, end_ts, "
                    f"substr(text, 1, 500) AS text "
                    f"FROM chunks WHERE {where} LIMIT {int(limit)}"
                )
                cur = con.execute(sql, qparams)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        if not reuse:
            con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    add_root_arg(ap)
    ap.add_argument("--sql")
    ap.add_argument("--text")
    ap.add_argument("--platform")
    ap.add_argument("--year")
    ap.add_argument("--author")
    ap.add_argument("--start-ts")
    ap.add_argument("--end-ts")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()
    try:
        rows = query(
            args.root,
            sql=args.sql,
            text=args.text,
            platform=args.platform,
            year=args.year,
            author=args.author,
            start_ts=args.start_ts,
            end_ts=args.end_ts,
            limit=args.limit,
        )
    except FtsMissing as e:
        print(str(e), file=sys.stderr)
        return 2
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(rows, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
