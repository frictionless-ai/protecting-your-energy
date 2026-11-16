#!/usr/bin/env python3
"""Hybrid BM25 + dense retrieval with RRF and optional cross-encoder rerank.

Dense vectors: BGE-M3 when sentence-transformers is installed, otherwise a
documented hash embedding so the pipeline is testable without a GPU.
Vectors live in Parquet (not DuckDB VSS). LanceDB is used when installed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import add_root_arg, derived_dir, resolve_root, sha256_text  # noqa: E402

HASH_DIM = 256
RRF_K = 60
META_NAME = "hybrid_meta.json"


def hash_embed(texts: Iterable[str], dim: int = HASH_DIM) -> np.ndarray:
    """Deterministic bag-of-bytes embedding. Not BGE-M3 — used when GPU/models absent."""
    out = []
    for t in texts:
        v = np.zeros(dim, dtype=np.float32)
        b = (t or "").encode("utf-8", errors="surrogatepass")
        if not b:
            out.append(v)
            continue
        for i in range(len(b) - 1):
            h = (b[i] * 131 + b[i + 1]) % dim
            v[h] += 1.0
        n = np.linalg.norm(v)
        if n:
            v /= n
        out.append(v)
    return np.vstack(out) if out else np.zeros((0, dim), dtype=np.float32)


_ST_MODELS: dict = {}


def st_embed(texts: list[str], model_name: str) -> tuple[np.ndarray, str] | None:
    """Encode with any sentence-transformers model, cached per process."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    model = _ST_MODELS.get(model_name)
    if model is None:
        model = SentenceTransformer(model_name)
        _ST_MODELS[model_name] = model
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32), model_name


def try_bge_embed(texts: list[str]) -> tuple[np.ndarray, str] | None:
    return st_embed(texts, "BAAI/bge-m3")


def _chunk_files(root: str) -> list[str]:
    base = os.path.join(derived_dir(root), "chunks")
    files = []
    for dp, _, fns in os.walk(base):
        files.extend(os.path.join(dp, f) for f in fns if f.endswith(".parquet"))
    if not files:
        raise SystemExit(f"no chunks under {base}")
    return sorted(files)


def build_hybrid(root: str, require_dense_model: bool = False) -> dict:
    root = resolve_root(root)
    files = _chunk_files(root)
    model_name = "hash_embed"
    probe = try_bge_embed(["availability probe"])
    if probe:
        model_name = "BAAI/bge-m3"
    elif require_dense_model:
        raise SystemExit("BGE-M3 unavailable and --require-dense-model was set")
    out_dir = os.path.join(derived_dir(root), "hybrid")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "embeddings.parquet")
    writer = None
    n = 0
    dim = HASH_DIM
    for fp in files:
        t = pq.ParquetFile(fp).read()
        texts = t.column("text").to_pylist()
        ids = t.column("chunk_id").to_pylist()
        if model_name == "BAAI/bge-m3":
            got = try_bge_embed(texts)
            vecs = got[0] if got else hash_embed(texts)
        else:
            vecs = hash_embed(texts)
        dim = int(vecs.shape[1])
        years = t.column("year").to_pylist() if "year" in t.column_names else [""] * len(ids)
        years = [str(y) if y is not None else "" for y in years]
        table = pa.table({
            "chunk_id": ids,
            "conversation_id": t.column("conversation_id").to_pylist(),
            "platform": t.column("platform").to_pylist(),
            "year": years,
            "level": ["chunk"] * len(ids),
            "embedding": [v.tolist() for v in vecs],
        })
        if writer is None:
            writer = pq.ParquetWriter(path, table.schema, compression="zstd")
        writer.write_table(table)
        n += len(ids)
        del vecs, table, texts
    if writer is not None:
        writer.close()
    if n == 0:
        raise SystemExit(f"no chunks under {os.path.join(derived_dir(root), 'chunks')}")
    lancedb_ok = False
    if n <= 10_000:
        try:
            import lancedb
            db = lancedb.connect(os.path.join(out_dir, "lancedb"))
            db.create_table("chunks", pq.read_table(path).to_pandas(), mode="overwrite")
            lancedb_ok = True
        except Exception:
            lancedb_ok = False
    meta = {
        "model": model_name,
        "dim": dim,
        "n": n,
        "path": path,
        "lancedb": lancedb_ok,
        "rrf_k": RRF_K,
        "reranker": "BAAI/bge-reranker-v2-m3 (optional)",
        "bge_m3_available": model_name == "BAAI/bge-m3",
        "gap": None if model_name == "BAAI/bge-m3" else
        "sentence-transformers / BGE-M3 not installed; hash embeddings used. "
        "Install sentence-transformers and a GPU to replace hash_embed.",
    }
    with open(os.path.join(out_dir, META_NAME), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    return meta


def rrf(rank_lists: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for lst in rank_lists:
        for rank, cid in enumerate(lst, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


_DENSE_CACHE: tuple | None = None


def dense_search(root: str, query: str, limit: int = 50) -> list[str]:
    global _DENSE_CACHE
    hybrid = os.path.join(derived_dir(root), "hybrid")
    files = []
    main = os.path.join(hybrid, "embeddings.parquet")
    extra = os.path.join(hybrid, "embeddings_year.parquet")
    if os.path.isfile(main):
        files.append(main)
    if os.path.isfile(extra):
        files.append(extra)
    if not files:
        return []
    meta_path = os.path.join(hybrid, META_NAME)
    model = "hash_embed"
    if os.path.isfile(meta_path):
        model = json.load(open(meta_path)).get("model") or model
    cache_key = tuple(files) + (model,)
    if _DENSE_CACHE is None or _DENSE_CACHE[0] != cache_key:
        ids: list[str] = []
        mats = []
        for fp in files:
            table = pq.ParquetFile(fp).read()
            ids.extend(table.column("chunk_id").to_pylist())
            mats.append(np.asarray(table.column("embedding").to_pylist(), dtype=np.float32))
        mat = np.vstack(mats) if mats else np.zeros((0, HASH_DIM), dtype=np.float32)
        _DENSE_CACHE = (cache_key, ids, mat, model)
    _, ids, mat, model = _DENSE_CACHE
    if model != "hash_embed":
        got = st_embed([query], model)
        q = got[0][0] if got else hash_embed([query])[0]
        if q.shape[0] != mat.shape[1]:
            q = hash_embed([query])[0]
    else:
        q = hash_embed([query])[0]
    sims = mat @ q
    order = np.argsort(-sims)[:limit]
    return [ids[i] for i in order]


def try_rerank(query: str, docs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    if not docs:
        return docs
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        return docs
    try:
        name = os.environ.get("UPAR_RERANKER", "cross-encoder/ms-marco-MiniLM-L6-v2")
        model = _ST_MODELS.get(("ce", name))
        if model is None:
            model = CrossEncoder(name)
            _ST_MODELS[("ce", name)] = model
        scores = model.predict([[query, text] for _, text in docs])
        ranked = sorted(zip(scores, docs), key=lambda x: -float(x[0]))
        return [d for _, d in ranked]
    except Exception:
        return docs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    add_root_arg(ap)
    ap.add_argument("--require-dense-model", action="store_true")
    args = ap.parse_args()
    print(json.dumps(build_hybrid(args.root, require_dense_model=args.require_dense_model), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
