#!/usr/bin/env python3
"""MCP primitive server over derived UPAR views.

Tools: sql_query, hybrid_search, graph_search, get_summary, get_case, list_capabilities.
Optional: append_memory_note. sql_query is SELECT-only.
Cloudflare McpAgent / AIChatAgent is a later wrapper around this process.

Speaks LSP Content-Length framing (Cursor). NDJSON lines are still accepted.
Heavy imports (DuckDB / pyarrow / hybrid) are deferred until a tool needs them
so initialize + tools/list stay inside the MCP proxy budget.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import derived_dir, resolve_root  # noqa: E402
from stdio_framing import read_message, write_message  # noqa: E402

TOOLS = [
    {
        "name": "sql_query",
        "description": "Read-only SELECT over Hive Parquet (messages, chunks, cases, summaries) via in-memory DuckDB.",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
    {
        "name": "hybrid_search",
        "description": "BM25 + dense RRF search over conversation chunks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "platform": {"type": "string"},
                "year": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "graph_search",
        "description": "Search the Graphiti temporal graph. Returns not_loaded when the graph is empty.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "get_summary",
        "description": "Fetch time-first summaries by level (conversation, month_platform, year, era).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "year": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_case",
        "description": "Fetch a behavioral case by case_id or source_record_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "source_record_id": {"type": "string"},
            },
        },
    },
    {
        "name": "list_capabilities",
        "description": "List retrieval tools and privacy rules.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "append_memory_note",
        "description": "Append a note to derived/memory/notes.jsonl (the only write tool).",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


class RetrievalTools:
    def __init__(self, root: str):
        self.root = resolve_root(root)

    def list_capabilities(self, **_):
        return {
            "tools": [t["name"] for t in TOOLS],
            "privacy": "Private corpus. Use derived text only within authorized source policy.",
            "workspace": derived_dir(self.root),
        }

    def sql_query(self, sql: str = "", **_):
        from query_sql import FtsMissing, assert_readonly_sql, query as sql_query_impl

        assert_readonly_sql(sql)
        try:
            return {"rows": sql_query_impl(self.root, sql=sql, reuse=True)}
        except FtsMissing as e:
            return {"error": "fts_missing", "message": str(e)}

    def hybrid_search(self, text: str = "", platform: str | None = None,
                      year: str | None = None, limit: int = 10, **_):
        if os.environ.get("UPAR_HYBRID_FULL", "").strip() in {"1", "true", "yes"}:
            from search import search as hybrid_search_impl

            rows, warnings = hybrid_search_impl(
                self.root, text, platform=platform, year=year, limit=int(limit or 10),
                rerank=False, skip_dense=True,
            )
            return {"hits": rows, "warnings": warnings}
        from local_fallback import bounded_search

        out = bounded_search(
            self.root, text, platform=platform, year=year, limit=int(limit or 10),
        )
        out.pop("fallback", None)
        return out

    def graph_search(self, text: str = "", **_):
        state = os.path.join(derived_dir(self.root), "graphiti", "load_state.json")
        if not os.path.isfile(state):
            return {"error": "not_loaded", "message": "Graphiti has not been loaded"}
        st = json.load(open(state, encoding="utf-8"))
        if not st.get("ok") or not st.get("loaded"):
            return {
                "error": "not_loaded",
                "message": "Graphiti graph is empty or load failed",
                "state": {k: st.get(k) for k in ("prepared", "loaded", "ok", "error")},
            }
        return {
            "error": "not_implemented_live",
            "message": "Graph is marked loaded; call Graphiti search from the host with GRAPHITI_NEO4J_URI",
            "loaded": st.get("loaded"),
            "query": text,
        }

    def get_summary(self, level: str | None = None, year: str | None = None, limit: int = 20, **_):
        from query_sql import FtsMissing, query as sql_query_impl

        try:
            clauses = ["1=1"]
            params: list = []
            if level:
                clauses.append("level = ?")
                params.append(level)
            if year:
                clauses.append("year = ?")
                params.append(year)
            sql = (
                "SELECT summary_id, level, year, month, platform, era, n_sources, "
                "substr(text, 1, 800) AS text, status FROM summaries WHERE "
                + " AND ".join(clauses)
                + f" LIMIT {int(limit or 20)}"
            )
            return {"rows": sql_query_impl(self.root, sql=sql, params=params, reuse=True)}
        except FtsMissing as e:
            return {"error": "fts_missing", "message": str(e)}
        except Exception as e:
            return {"error": "query_failed", "message": str(e)}

    def get_case(self, case_id: str | None = None, source_record_id: str | None = None, **_):
        from query_sql import FtsMissing, query as sql_query_impl

        if not case_id and not source_record_id:
            return {"error": "missing_id"}
        try:
            if case_id:
                safe = case_id.replace("'", "")
                sql = f"SELECT * FROM cases WHERE case_id = '{safe}' LIMIT 5"
            else:
                safe = (source_record_id or "").replace("'", "")
                sql = f"SELECT * FROM cases WHERE source_record_id = '{safe}' LIMIT 20"
            return {"rows": sql_query_impl(self.root, sql=sql, reuse=True)}
        except FtsMissing as e:
            return {"error": "fts_missing", "message": str(e)}

    def append_memory_note(self, text: str = "", **_):
        mem = os.path.join(derived_dir(self.root), "memory")
        os.makedirs(mem, exist_ok=True)
        path = os.path.join(mem, "notes.jsonl")
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": text,
        }
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return {"ok": True, "path": path}


def dispatch(tools: RetrievalTools, name: str, arguments: dict):
    """Primary tool call with automatic local fallback on timeout/failure."""
    from retrieve import call_tool

    return call_tool(tools.root, name, arguments or {})


def mcp_loop(tools: RetrievalTools) -> None:
    """Stdio JSON-RPC MCP (initialize, tools/list, tools/call) with Content-Length."""
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        try:
            msg = read_message(stdin)
        except json.JSONDecodeError:
            continue
        if msg is None:
            break
        mid = msg.get("id")
        method = msg.get("method")
        result = None
        error = None
        if method == "initialize":
            client_ver = (msg.get("params") or {}).get("protocolVersion") or "2024-11-05"
            result = {
                "protocolVersion": client_ver,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "upar-retrieval", "version": "1.1.0"},
            }
        elif method in {
            "notifications/initialized",
            "notifications/cancelled",
            "initialized",
        }:
            continue
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            try:
                payload = dispatch(tools, name, arguments)
                result = {
                    "content": [{"type": "text", "text": json.dumps(payload, default=str)}],
                }
            except Exception as e:  # keep the loop alive on tool failures
                result = {
                    "content": [{"type": "text", "text": json.dumps(
                        {"error": "tool_failed", "tool": name, "message": str(e)})}],
                    "isError": True,
                }
        else:
            error = {"code": -32601, "message": f"unknown method {method}"}
        if mid is None and error is None:
            continue
        resp = {"jsonrpc": "2.0", "id": mid}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        write_message(stdout, resp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    env_root = os.environ.get("UPAR_ROOT")
    ap.add_argument(
        "--root",
        required=not env_root,
        default=env_root,
        help="Archive root (or set UPAR_ROOT).",
    )
    ap.add_argument("--stdio", action="store_true", default=True)
    args = ap.parse_args()
    tools = RetrievalTools(args.root)
    mcp_loop(tools)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
