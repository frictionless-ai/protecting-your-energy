#!/usr/bin/env python3
"""Fuse BM25 and dense ranks (RRF), then optional cross-encoder rerank."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_hybrid import dense_search, rrf, try_rerank  # noqa: E402
from common import add_root_arg, derived_dir, resolve_root  # noqa: E402
from query_sql import FtsMissing, query  # noqa: E402


def _hydrate_chunks(root: str, ids: list[str]) -> dict[str, dict]:
    """Fill chunk_id → row for dense-only hits that BM25 did not return."""
    if not ids:
        return {}
    safe = [i.replace("'", "") for i in ids if i]
    if not safe:
        return {}
    quoted = ",".join(f"'{i}'" for i in safe)
    try:
        rows = query(
            root,
            sql=(
                "SELECT chunk_id, conversation_id, platform, year, start_ts, end_ts, "
                f"substr(text, 1, 800) AS text FROM chunks WHERE chunk_id IN ({quoted})"
            ),
        )
        return {r["chunk_id"]: r for r in rows if r.get("chunk_id")}
    except (FtsMissing, Exception):
        pass
    from common import derived_dir, read_parquet_tree
    base = os.path.join(derived_dir(root), "chunks")
    try:
        cols = read_parquet_tree(base)
    except FileNotFoundError:
        return {}
    wanted = set(safe)
    out = {}
    for i, cid in enumerate(cols.get("chunk_id") or []):
        if cid in wanted:
            out[cid] = {k: cols[k][i] for k in cols}
            text = out[cid].get("text") or ""
            out[cid]["text"] = text[:800]
    return out


def search(
    root: str,
    text: str,
    *,
    platform: str | None = None,
    year: str | None = None,
    limit: int = 10,
    require_dense: bool = False,
    rerank: bool = True,
    skip_dense: bool = False,
) -> tuple[list[dict], list[str]]:
    if not (text or "").strip():
        raise ValueError("empty query")
    root = resolve_root(root)
    warnings: list[str] = []
    bm25_ids: list[str] = []
    try:
        rows = query(root, text=text, platform=platform, year=year, limit=50)
        bm25_ids = [r["chunk_id"] for r in rows if r.get("chunk_id")]
        by_id = {r["chunk_id"]: r for r in rows}
    except FtsMissing as e:
        warnings.append(str(e))
        by_id = {}
        if require_dense:
            pass
    if skip_dense:
        dense_ids = []
        warnings.append("dense skipped")
    else:
        dense_ids = dense_search(root, text, limit=50)
    if not dense_ids and not skip_dense:
        warnings.append("dense index missing or empty; BM25-only")
        if require_dense:
            raise SystemExit("dense index unavailable and --require-dense was set")
    fused = rrf([lst for lst in (bm25_ids, dense_ids) if lst])
    top = fused[: max(limit * 5, 50)]
    missing = [cid for cid, _ in top if cid not in by_id or not (by_id[cid].get("text"))]
    if missing:
        by_id.update(_hydrate_chunks(root, missing))
    # hydrate text
    docs: list[tuple[str, str]] = []
    for cid, _score in top:
        row = by_id.get(cid)
        snippet = (row or {}).get("text") or ""
        docs.append((cid, snippet))
    if rerank:
        docs = try_rerank(text, docs)
    out = []
    for cid, snippet in docs[:limit]:
        row = dict(by_id.get(cid) or {"chunk_id": cid, "text": snippet})
        row["text"] = snippet or row.get("text")
        out.append(row)
    return out, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    add_root_arg(ap)
    ap.add_argument("--text", required=True)
    ap.add_argument("--platform")
    ap.add_argument("--year")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--require-dense", action="store_true")
    ap.add_argument("--no-rerank", action="store_true")
    args = ap.parse_args()
    try:
        rows, warnings = search(
            args.root,
            args.text,
            platform=args.platform,
            year=args.year,
            limit=args.limit,
            require_dense=args.require_dense,
            rerank=not args.no_rerank,
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    for w in warnings:
        print(w, file=sys.stderr)
    print(json.dumps(rows, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
