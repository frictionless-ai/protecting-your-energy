"""In-process UPAR retrieval router.

Primary path is the existing RetrievalTools / hybrid / SQL stack.
On timeout, hang-class errors, or 5xx-like failures, run local_fallback
without talking to an MCP process.
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BUDGET_S = float(os.environ.get("UPAR_QUERY_BUDGET_S", "12"))
FORCE_FAIL = os.environ.get("UPAR_FORCE_PRIMARY_FAIL", "").strip() in {"1", "true", "yes"}

_FAIL_MARKERS = (
    "timed out",
    "timeout",
    "time out",
    "connection refused",
    "connection reset",
    "broken pipe",
    "unavailable",
    "503",
    "502",
    "500",
    "-32001",
)


def _short(exc: BaseException) -> str:
    msg = f"{type(exc).__name__}: {exc}"
    return msg[:240]


def _is_fail(exc: BaseException) -> bool:
    blob = str(exc).lower()
    if isinstance(exc, (TimeoutError, FuturesTimeout, ConnectionError, OSError)):
        return True
    return any(m in blob for m in _FAIL_MARKERS)


def run_with_budget(fn: Callable[[], Any], budget_s: float) -> Any:
    if budget_s <= 0:
        return fn()
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        try:
            return fut.result(timeout=budget_s)
        except FuturesTimeout as e:
            try:
                from query_sql import _CACHED_CON
                for con in list(_CACHED_CON.values()):
                    try:
                        con.interrupt()
                    except Exception:
                        pass
            except Exception:
                pass
            raise TimeoutError(f"primary exceeded {budget_s:.1f}s") from e


def _primary(root: str, name: str, arguments: dict) -> Any:
    import mcp_server

    tools = mcp_server.RetrievalTools(root)
    if not hasattr(tools, name) or name.startswith("_"):
        return {"error": "unknown_tool", "name": name}
    return getattr(tools, name)(**(arguments or {}))


def call_tool(
    root: str,
    name: str,
    arguments: dict | None = None,
    *,
    budget_s: float | None = None,
    force_fallback: bool = False,
) -> dict[str, Any]:
    from local_fallback import fallback_tool

    args = arguments or {}
    budget = DEFAULT_BUDGET_S if budget_s is None else float(budget_s)
    if force_fallback or FORCE_FAIL:
        return fallback_tool(root, name, args, reason="forced_primary_fail")
    try:
        result = run_with_budget(lambda: _primary(root, name, args), budget)
        if isinstance(result, dict) and result.get("error") in {
            "tool_failed",
            "query_failed",
            "fts_missing",
        }:
            fb = fallback_tool(root, name, args, reason=str(result.get("message") or result["error"]))
            if name in {"hybrid_search", "sql_query", "list_capabilities", "get_summary"}:
                return fb
        return result
    except Exception as e:
        if not _is_fail(e) and name not in {"hybrid_search", "sql_query", "list_capabilities"}:
            return {"error": "tool_failed", "tool": name, "message": _short(e)}
        return fallback_tool(root, name, args, reason=_short(e))
