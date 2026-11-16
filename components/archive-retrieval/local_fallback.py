"""Bounded local retrieval. No MCP process. No engine files on the USB tree.

Used when the primary MCP/hybrid/SQL path times out, hangs, or raises.
Queries stay year/platform/limit bounded so they do not scan 3.4M rows.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import derived_dir, resolve_root  # noqa: E402

DEFAULT_YEARS = tuple(
    y.strip()
    for y in os.environ.get("UPAR_DEFAULT_YEARS", "2026,2025,2024").split(",")
    if y.strip()
)
MAX_LIMIT = 50
LIKE_UNSAFE = re.compile(r"[%_\\]")


def _available_years(root: str) -> set[str]:
    base = os.path.join(derived_dir(root), "chunks")
    found: set[str] = set()
    if not os.path.isdir(base):
        return found
    for name in os.listdir(base):
        if name.startswith("year="):
            found.add(name.split("=", 1)[1])
    return found


def _years(year: str | None, root: str | None = None) -> list[str]:
    if year:
        return [str(year)]
    if root:
        present = _available_years(root)
        chosen = [y for y in DEFAULT_YEARS if y in present]
        if chosen:
            return chosen
        return []
    return list(DEFAULT_YEARS)


def _limit(limit: int | None) -> int:
    try:
        n = int(limit or 10)
    except (TypeError, ValueError):
        n = 10
    return max(1, min(n, MAX_LIMIT))


def _escape_like(text: str) -> str:
    return LIKE_UNSAFE.sub(lambda m: "\\" + m.group(0), text or "")


def capabilities(root: str | None = None) -> dict[str, Any]:
    workspace = None
    if root:
        try:
            workspace = derived_dir(resolve_root(root))
        except SystemExit:
            workspace = None
    return {
        "tools": [
            "sql_query",
            "hybrid_search",
            "graph_search",
            "get_summary",
            "get_case",
            "list_capabilities",
            "append_memory_note",
        ],
        "privacy": "Private corpus. Use derived text only within authorized source policy.",
        "workspace": workspace,
        "fallback": True,
        "bounded_years": list(DEFAULT_YEARS),
    }


def _connect(root: str):
    from query_sql import connect_cached

    return connect_cached(resolve_root(root))


def bounded_search(
    root: str,
    text: str,
    *,
    platform: str | None = None,
    year: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    if not (text or "").strip():
        return {"error": "empty_query", "hits": [], "fallback": True}
    years = _years(year, root)
    lim = _limit(limit)
    needle = f"%{_escape_like(text.strip())}%"
    clauses: list[str] = []
    params: list[Any] = []
    if years:
        clauses.append("CAST(year AS VARCHAR) IN ({})".format(",".join("?" * len(years))))
        params.extend(years)
    if platform:
        clauses.append("platform = ?")
        params.append(platform)
    clauses.append("text ILIKE ? ESCAPE '\\'")
    params.append(needle)
    sql = (
        "SELECT chunk_id, conversation_id, platform, year, start_ts, end_ts, "
        "substr(text, 1, 400) AS text "
        f"FROM chunks WHERE {' AND '.join(clauses) if clauses else '1=1'} "
        f"LIMIT {lim}"
    )
    con = _connect(root)
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    hits = [dict(zip(cols, row)) for row in cur.fetchall()]
    return {
        "hits": hits,
        "warnings": ["bounded_parquet_fallback"],
        "fallback": True,
        "years": years,
        "limit": lim,
    }


def bounded_sql(
    root: str,
    sql: str | None = None,
    *,
    year: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Degrade arbitrary SQL to a year-bounded chunks probe, or a tight SELECT."""
    from query_sql import assert_readonly_sql

    years = _years(year, root)
    lim = _limit(limit)
    con = _connect(root)
    raw = (sql or "").strip()
    if raw:
        try:
            safe = assert_readonly_sql(raw)
        except ValueError as e:
            return {"error": "invalid_sql", "message": str(e), "fallback": True, "rows": []}
        if not re.search(r"\bLIMIT\b", safe, re.I):
            safe = f"{safe} LIMIT {lim}"
        if re.search(r"\bmessages\b", safe, re.I) and not re.search(
            r"\byear\b|\bplatform\b", safe, re.I
        ):
            # Refuse to become the naive full scan. Probe recent partitions instead.
            cur = con.execute(
                "SELECT CAST(year AS VARCHAR) AS year, count(*) AS n "
                "FROM messages WHERE CAST(year AS VARCHAR) IN ({}) "
                "GROUP BY 1 ORDER BY 1 DESC".format(",".join("?" * len(years))),
                list(years),
            )
            cols = [d[0] for d in cur.description]
            return {
                "rows": [dict(zip(cols, row)) for row in cur.fetchall()],
                "fallback": True,
                "warnings": ["unbounded_messages_sql_rewritten_to_year_counts"],
                "years": years,
            }
        cur = con.execute(safe)
        cols = [d[0] for d in cur.description]
        return {"rows": [dict(zip(cols, row)) for row in cur.fetchall()], "fallback": True}
    cur = con.execute(
        "SELECT count(*) AS n_chunks FROM chunks WHERE CAST(year AS VARCHAR) IN ({})".format(
            ",".join("?" * len(years))
        ),
        list(years),
    )
    cols = [d[0] for d in cur.description]
    return {"rows": [dict(zip(cols, row)) for row in cur.fetchall()], "fallback": True, "years": years}


def bounded_summaries(
    root: str,
    *,
    level: str | None = None,
    year: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    lim = _limit(limit)
    clauses = ["1=1"]
    params: list[Any] = []
    if level:
        clauses.append("level = ?")
        params.append(level)
    if year:
        clauses.append("CAST(year AS VARCHAR) = ?")
        params.append(str(year))
    sql = (
        "SELECT summary_id, level, year, month, platform, era, n_sources, "
        "substr(text, 1, 400) AS text, status FROM summaries WHERE "
        + " AND ".join(clauses)
        + f" LIMIT {lim}"
    )
    try:
        con = _connect(root)
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return {"rows": [dict(zip(cols, row)) for row in cur.fetchall()], "fallback": True}
    except Exception as e:
        return {"error": "query_failed", "message": str(e), "fallback": True, "rows": []}


def fallback_tool(root: str, name: str, arguments: dict | None, reason: str) -> dict[str, Any]:
    args = arguments or {}
    if name == "list_capabilities":
        out = capabilities(root)
        out["fallback_reason"] = reason
        return out
    if name == "hybrid_search":
        out = bounded_search(
            root,
            args.get("text") or "",
            platform=args.get("platform"),
            year=args.get("year"),
            limit=int(args.get("limit") or 10),
        )
        out["fallback_reason"] = reason
        return out
    if name == "sql_query":
        out = bounded_sql(root, args.get("sql"), year=args.get("year"), limit=20)
        out["fallback_reason"] = reason
        return out
    if name == "get_summary":
        out = bounded_summaries(
            root,
            level=args.get("level"),
            year=args.get("year"),
            limit=int(args.get("limit") or 20),
        )
        out["fallback_reason"] = reason
        return out
    if name == "graph_search":
        return {
            "error": "not_loaded",
            "message": "Graphiti fallback: graph is not queried locally",
            "fallback": True,
            "fallback_reason": reason,
            "query": args.get("text") or "",
        }
    if name == "get_case":
        return {"error": "fallback_no_case_index", "fallback": True, "fallback_reason": reason}
    return {"error": "unknown_tool", "name": name, "fallback": True, "fallback_reason": reason}
