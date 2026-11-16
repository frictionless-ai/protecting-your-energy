"""Shared helpers for derived retrieval. No hardcoded /home or /run/media defaults."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterator

ERROR_RATE_THRESHOLD = 0.01
WINDOW_MESSAGES = 20
WINDOW_OVERLAP = 5
GAP_SECONDS = 1800
MAX_CHUNK_TOKENS = 512

def _strings(value, key):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError('archive policy requires a string array for ' + key)
    return [item.strip() for item in value]


def _private_policy():
    default = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'protecting-your-energy/archive-policy.json'
    path = Path(os.environ.get('PYE_ARCHIVE_POLICY_FILE') or default).expanduser()
    if not path.exists():
        if os.environ.get('PYE_ARCHIVE_POLICY_FILE'):
            raise ValueError('configured archive policy file is unavailable')
        return {}, 'unconfigured'
    with path.open('rb') as handle:
        raw = handle.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('archive policy exceeds one MiB')
    policy = json.loads(raw)
    if not isinstance(policy, dict):
        raise ValueError('archive policy must be an object')
    return policy, 'configured'


_POLICY, POLICY_STATUS = _private_policy()
OWNER_DISCORD_ID = os.environ.get('THOUGHT_RECONSTRUCTION_OWNER_ID', _POLICY.get('owner_discord_id', ''))
if not isinstance(OWNER_DISCORD_ID, str):
    raise ValueError('archive policy owner_discord_id must be a string')
_aliases = json.loads(os.environ['THOUGHT_RECONSTRUCTION_OWNER_ALIASES']) if 'THOUGHT_RECONSTRUCTION_OWNER_ALIASES' in os.environ else _POLICY.get('owner_aliases', [])
OWNER_ALIASES = frozenset(item.casefold() for item in _strings(_aliases, 'owner_aliases'))
ALLOWED_SOURCE_ROOTS = []
for _value in _strings(_POLICY.get('allowed_source_roots', []), 'allowed_source_roots'):
    _path = Path(_value).expanduser()
    if not _path.is_absolute():
        raise ValueError('archive policy allowed_source_roots must be absolute')
    ALLOWED_SOURCE_ROOTS.append(_path.resolve(strict=False))


class _HashedNames(frozenset):
    """Excluded display names, stored as sha256 of the lowercased name so the
    name itself never appears in code or in emitted records."""

    def __contains__(self, name: object) -> bool:
        key = str(name or "").strip().lower().encode("utf-8")
        return frozenset.__contains__(self, hashlib.sha256(key).hexdigest())


EXCLUDED_IDS = set(_strings(_POLICY.get('excluded_author_ids', []), 'excluded_author_ids'))
_name_hashes = _strings(_POLICY.get('excluded_name_hashes', []), 'excluded_name_hashes')
if any(not re.fullmatch(r'[0-9a-f]{64}', item) for item in _name_hashes):
    raise ValueError('archive policy excluded_name_hashes must contain lowercase SHA256 values')
EXCLUDED_NAMES = _HashedNames(_name_hashes)

ERA_BANDS = (
    ("2008-2012", 2008, 2012),
    ("2013-2016", 2013, 2016),
    ("2017-2020", 2017, 2020),
    ("2021-2023", 2021, 2023),
    ("2024-2026", 2024, 2026),
)


def add_root_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--root",
        required=True,
        help="Archive root (the directory that contains archive/ and tooling/). "
        "Required so builders never bake in /home or /run/media paths.",
    )


def resolve_root(root: str) -> str:
    if not root:
        raise SystemExit("--root is required")
    path = os.path.abspath(root)
    if not os.path.isdir(path):
        raise SystemExit(f"--root does not exist: {path}")
    return path


def derived_dir(root: str) -> str:
    return os.path.join(root, "archive", "corpus", "derived")


def records_dir(root: str) -> str:
    return os.path.join(root, "archive", "corpus", "records")


def approx_tokens(text: str) -> int:
    return max(1, (len(text or "") + 3) // 4)


def year_from_ts(ts: str | None) -> str:
    if not ts:
        return "unknown"
    m = re.match(r"^(\d{4})", ts)
    if not m:
        return "unknown"
    y = int(m.group(1))
    if y < 1970 or y > 2100:
        return "unknown"
    return f"{y:04d}"


def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        s = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def sha256_text(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", errors="surrogatepass"))
        h.update(b"\x00")
    return h.hexdigest()


def iter_jsonl(path: str) -> Iterator[tuple[int, dict | None, str | None]]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                yield i, None, str(e)
                continue
            if not isinstance(obj, dict):
                yield i, None, "not an object"
                continue
            yield i, obj, None


def iter_conversation_records(root: str) -> Iterator[tuple[str, dict | None, str | None]]:
    conv_root = os.path.join(records_dir(root), "kind=conversation")
    if not os.path.isdir(conv_root):
        return
    for dirpath, _, filenames in os.walk(conv_root):
        for fn in sorted(filenames):
            if not fn.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            for lineno, obj, err in iter_jsonl(path):
                yield f"{rel}:{lineno}", obj, err


def message_text(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for part in c:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text") or part.get("content") or "")
        return "\n".join(p for p in parts if p)
    return ""


def author_id(msg: dict) -> str | None:
    au = msg.get("author") or {}
    return au.get("id") or msg.get("name")


def author_name(msg: dict) -> str | None:
    au = msg.get("author") or {}
    return au.get("name") or msg.get("name")


def author_role(msg: dict) -> str:
    au = msg.get("author") or {}
    return (au.get("role") or msg.get("role") or "unknown").lower()


def is_boden_alias(pid: str | None, name: str | None) -> bool:
    ids = (pid or "").strip()
    nm = (name or "").strip().lower()
    if ids in EXCLUDED_IDS or nm in EXCLUDED_NAMES:
        return False
    if OWNER_DISCORD_ID and ids == OWNER_DISCORD_ID:
        return True
    if ids.lower() in OWNER_ALIASES or nm in OWNER_ALIASES:
        return True
    if nm in OWNER_ALIASES:
        return True
    return False


def is_excluded_identity(pid: str | None, name: str | None) -> bool:
    ids = (pid or "").strip()
    nm = (name or "").strip().lower()
    return ids in EXCLUDED_IDS or nm in EXCLUDED_NAMES


def era_for_year(year: str) -> str:
    try:
        y = int(year)
    except ValueError:
        return "unknown"
    for name, lo, hi in ERA_BANDS:
        if lo <= y <= hi:
            return name
    return "unknown"


def chunk_windows(
    messages: list[dict],
    window: int = WINDOW_MESSAGES,
    overlap: int = WINDOW_OVERLAP,
    gap_seconds: int = GAP_SECONDS,
    max_tokens: int = MAX_CHUNK_TOKENS,
) -> list[tuple[int, int]]:
    """Return (start, end) index pairs, end exclusive."""
    n = len(messages)
    if n == 0:
        return []
    segments: list[list[int]] = []
    current = [0]
    prev_dt = parse_ts(messages[0].get("sent_at"))
    for i in range(1, n):
        dt = parse_ts(messages[i].get("sent_at"))
        split = False
        if prev_dt and dt:
            split = (dt - prev_dt).total_seconds() > gap_seconds
        if split:
            segments.append(current)
            current = [i]
        else:
            current.append(i)
        if dt:
            prev_dt = dt
    segments.append(current)

    spans: list[tuple[int, int]] = []
    for seg in segments:
        start = seg[0]
        end_limit = seg[-1] + 1
        i = start
        while i < end_limit:
            j = min(i + window, end_limit)
            tokens = 0
            k = i
            while k < j:
                tokens += approx_tokens(message_text(messages[k]))
                if tokens > max_tokens and k > i:
                    break
                k += 1
            j = max(i + 1, k)
            spans.append((i, j))
            if j >= end_limit:
                break
            nxt = j - overlap
            i = nxt if nxt > i else j
    return spans


def format_chunk_text(messages: list[dict], start: int, end: int) -> str:
    lines = []
    for m in messages[start:end]:
        role = author_role(m)
        name = author_name(m) or role
        lines.append(f"{role}/{name}: {message_text(m)}")
    return "\n".join(lines)


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def read_parquet_tree(base: str) -> dict:
    """Read Hive-partitioned Parquet without merging hive-inferred year (int)
    against the on-file year column (string). File-by-file, then concat."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    files = []
    for dirpath, _, filenames in os.walk(base):
        for fn in filenames:
            if fn.endswith(".parquet"):
                files.append(os.path.join(dirpath, fn))
    if not files:
        raise FileNotFoundError(f"no parquet files under {base}")
    tables = []
    for path in files:
        t = pq.ParquetFile(path).read()
        if "year" in t.column_names:
            idx = t.schema.get_field_index("year")
            t = t.set_column(idx, "year", t.column("year").cast(pa.string()))
        tables.append(t)
    return pa.concat_tables(tables, promote_options="default").to_pydict()
