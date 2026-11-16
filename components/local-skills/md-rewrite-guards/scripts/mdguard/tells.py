"""Tell scoring over prose spans and the durable per-target receipt (R4, R11, KTD7)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

from .scanner import ScanResult, scan
from .tokens import prose_tokens

#: Bundled marker table. Override the whole file with MDGUARD_MARKERS.
BUNDLED_MARKERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "markers.json")

#: A file scoring below this is clean and is never rewritten (R4). The value is
#: a default for callers; the CLI owns the final threshold.
CLEAN_THRESHOLD = 1

RECEIPT_KEYS = (
    "path",
    "original_sha256",
    "candidate_sha256",
    "score",
    "markers",
    "timestamp",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]")

_MARKER_CACHE: dict[tuple[str, int, int], "MarkerSet"] = {}


@dataclass(frozen=True)
class Marker:
    """One dated tell: its name, its compiled pattern, and why it is a tell."""

    name: str
    pattern: re.Pattern[str]
    rationale: str


@dataclass(frozen=True)
class MarkerSet:
    """A dated, revisable marker table loaded from a data file."""

    version: str
    source: str
    markers: tuple[Marker, ...]


@dataclass(frozen=True)
class TellScore:
    """Marker counts over prose only, with the prose word count they are measured against."""

    total: int
    per_marker: dict[str, int]
    prose_words: int


def markers_path() -> str:
    """Resolve the marker table path at call time, honoring MDGUARD_MARKERS."""
    override = os.environ.get("MDGUARD_MARKERS")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return BUNDLED_MARKERS


def load_markers() -> MarkerSet:
    """Load and compile the marker table, caching on path, size, and mtime."""
    path = markers_path()
    try:
        stat = os.stat(path)
    except OSError as exc:
        raise ValueError(f"marker table unreadable: {path}") from exc
    key = (path, stat.st_size, stat.st_mtime_ns)
    cached = _MARKER_CACHE.get(key)
    if cached is not None:
        return cached
    with open(path, "r", encoding="utf-8") as handle:
        try:
            raw = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"marker table is not valid JSON: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("markers"), list):
        raise ValueError(f"marker table has no marker list: {path}")
    entries = []
    for entry in raw["markers"]:
        if not isinstance(entry, dict):
            raise ValueError(f"marker entry is not an object: {path}")
        missing = [field for field in ("name", "pattern", "rationale") if not entry.get(field)]
        if missing:
            raise ValueError(f"marker entry missing {missing}: {path}")
        entries.append(
            Marker(entry["name"], re.compile(entry["pattern"], re.IGNORECASE), entry["rationale"])
        )
    loaded = MarkerSet(str(raw.get("version", "unversioned")), path, tuple(entries))
    _MARKER_CACHE[key] = loaded
    return loaded


def prose_blocks(result: ScanResult) -> tuple[str, ...]:
    """Return runs of contiguous prose lines, list markers stripped, frozen regions dropped."""
    markers = {
        region.start_line: region for region in result.regions if region.kind == "list_marker"
    }
    blocks: list[str] = []
    current: list[str] = []
    previous: int | None = None
    for index in result.prose_lines:
        line = result.lines[index]
        marker = markers.get(index)
        if marker is not None:
            line = line[len(marker.text) :]
        if previous is not None and index != previous + 1:
            blocks.append("\n".join(current))
            current = []
        current.append(line)
        previous = index
    if current:
        blocks.append("\n".join(current))
    return tuple(blocks)


def score(text: str) -> TellScore:
    """Count markers over prose only; text inside frozen regions never counts (R4)."""
    result = scan(text)
    table = load_markers()
    blocks = prose_blocks(result)
    per_marker: dict[str, int] = {}
    for marker in table.markers:
        hits = sum(len(marker.pattern.findall(block)) for block in blocks)
        if hits:
            per_marker[marker.name] = hits
    return TellScore(sum(per_marker.values()), per_marker, len(prose_tokens(result)))


def is_clean(value: TellScore, threshold: int = CLEAN_THRESHOLD) -> bool:
    """Report whether a score is at or below the clean threshold (R4, AE1)."""
    return value.total < threshold


def receipt_dir() -> str:
    """Resolve the receipt directory at call time, honoring MDGUARD_RECEIPT_DIR."""
    override = os.environ.get("MDGUARD_RECEIPT_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    cache = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(cache, "md-rewrite-guards", "receipts")


def receipt_path_for(target: str) -> str:
    """Derive the receipt path from the target's absolute path, deterministically (KTD7)."""
    absolute = os.path.abspath(os.path.expanduser(target))
    digest = hashlib.sha256(absolute.encode("utf-8")).hexdigest()[:16]
    name = SAFE_NAME_RE.sub("_", os.path.basename(absolute)) or "target"
    return os.path.join(receipt_dir(), f"{name}.{digest}.json")


def write_receipt(
    target: str,
    original_sha256: str,
    candidate_sha256: str | None,
    score: TellScore,
) -> str:
    """Write the receipt for ``target`` atomically and return its path (KTD7)."""
    table = load_markers()
    path = receipt_path_for(target)
    payload = {
        "path": os.path.abspath(os.path.expanduser(target)),
        "original_sha256": original_sha256,
        "candidate_sha256": candidate_sha256,
        "score": {
            "total": score.total,
            "per_marker": dict(sorted(score.per_marker.items())),
            "prose_words": score.prose_words,
        },
        "markers": {
            "version": table.version,
            "source": table.source,
            "fired": sorted(score.per_marker),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=os.path.dirname(path),
        prefix=".receipt-",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise
    return path


def read_receipt(path: str) -> dict:
    """Read a receipt, raising ValueError on anything malformed or truncated."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ValueError(f"receipt unreadable: {path}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"receipt is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"receipt is not an object: {path}")
    missing = [key for key in RECEIPT_KEYS if key not in payload]
    if missing:
        raise ValueError(f"receipt missing {missing}: {path}")
    if not isinstance(payload["path"], str) or not payload["path"]:
        raise ValueError(f"receipt path is not a string: {path}")
    if not isinstance(payload["original_sha256"], str) or not SHA256_RE.match(
        payload["original_sha256"]
    ):
        raise ValueError(f"receipt original_sha256 is not a sha256: {path}")
    candidate = payload["candidate_sha256"]
    if candidate is not None and not (isinstance(candidate, str) and SHA256_RE.match(candidate)):
        raise ValueError(f"receipt candidate_sha256 is not a sha256 or null: {path}")
    body = payload["score"]
    if not isinstance(body, dict):
        raise ValueError(f"receipt score is not an object: {path}")
    for field, kind in (("total", int), ("prose_words", int)):
        if not isinstance(body.get(field), kind) or isinstance(body.get(field), bool):
            raise ValueError(f"receipt score.{field} is not an integer: {path}")
    if not isinstance(body.get("per_marker"), dict):
        raise ValueError(f"receipt score.per_marker is not an object: {path}")
    if not isinstance(payload["markers"], dict) or not payload["markers"].get("version"):
        raise ValueError(f"receipt markers block has no version: {path}")
    if not isinstance(payload["timestamp"], str) or not payload["timestamp"]:
        raise ValueError(f"receipt timestamp is not a string: {path}")
    return payload


def receipt_identity(receipt: dict) -> dict:
    """Drop the fields excluded from identity comparison, which is timestamp alone."""
    return {key: value for key, value in receipt.items() if key != "timestamp"}
