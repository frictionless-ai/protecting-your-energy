#!/usr/bin/env python3
"""Local UPAR retrieval CLI. Does not start or require the MCP process.

Used automatically by mcp_server.py when a tool call times out or fails.
Agents can call this directly when Cursor reports MCP error -32001.

  upar_retrieve.py capabilities
  upar_retrieve.py search --text QUERY [--year 2026] [--platform discord] [--limit 10]
  upar_retrieve.py sql --sql 'SELECT count(*) FROM chunks WHERE year = 2026'
  upar_retrieve.py call --tool hybrid_search --args '{"text":"kotor","year":"2026"}'
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _root(args) -> str:
    root = args.root or os.environ.get("UPAR_ROOT")
    if not root:
        raise ValueError("archive root is required through --root or UPAR_ROOT")
    return root


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", help="Archive root (or UPAR_ROOT)")
    ap.add_argument("--force-fallback", action="store_true",
                    help="Skip primary path (same as UPAR_FORCE_PRIMARY_FAIL=1)")
    ap.add_argument("--budget", type=float, default=None, help="Primary budget seconds")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("capabilities")

    ps = sub.add_parser("search")
    ps.add_argument("--text", required=True)
    ps.add_argument("--year")
    ps.add_argument("--platform")
    ps.add_argument("--limit", type=int, default=10)

    pq = sub.add_parser("sql")
    pq.add_argument("--sql", required=True)

    pc = sub.add_parser("call")
    pc.add_argument("--tool", required=True)
    pc.add_argument("--args", default="{}", help="JSON object of tool arguments")

    args = ap.parse_args()
    from retrieve import call_tool

    root = _root(args)
    if args.cmd == "capabilities":
        name, arguments = "list_capabilities", {}
    elif args.cmd == "search":
        name, arguments = "hybrid_search", {
            "text": args.text,
            "year": args.year,
            "platform": args.platform,
            "limit": args.limit,
        }
    elif args.cmd == "sql":
        name, arguments = "sql_query", {"sql": args.sql}
    else:
        name = args.tool
        arguments = json.loads(args.args)

    out = call_tool(
        root, name, arguments,
        budget_s=args.budget,
        force_fallback=args.force_fallback,
    )
    # Counts and ids only in default mode — callers can pretty-print.
    print(json.dumps(out, indent=2, default=str, ensure_ascii=False))
    return 0 if not (isinstance(out, dict) and out.get("error") and not out.get("hits") and not out.get("rows")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
