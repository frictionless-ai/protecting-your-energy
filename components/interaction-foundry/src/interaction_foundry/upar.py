"""Streaming reader for the archive's UPAR conversation records.

The archive is a source record, not a release artifact.  This adapter keeps
the complete message sequence and source metadata private while exposing a
small, deterministic event shape to the existing ingestion pipeline.  It
never loads the corpus into memory: one JSON object is decoded at a time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, TextIO


_READ_CHUNK_BYTES = 64 * 1024
# The archive contains legitimate Discord conversations up to roughly 127 MiB.
# Keep a modest headroom while retaining a hard pre-decode allocation bound.
DEFAULT_MAX_RECORD_BYTES = 160 * 1024 * 1024


def _content(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(part for part in (_content(item) for item in value) if part)
    if isinstance(value, dict):
        return _content(value.get("text", value.get("content", value.get("parts", ""))))
    return ""


def _platform(record: dict) -> str:
    source = record.get("source")
    return str(source.get("platform", "")) if isinstance(source, dict) else ""


def _family(record: dict) -> str:
    source = record.get("source")
    return str(source.get("family", "")) if isinstance(source, dict) else ""


def _domain(record: dict) -> str | None:
    platform, family = _platform(record).casefold(), _family(record).casefold()
    if platform == "discord" or "discord" in family:
        return "discord"
    ai_platforms = {"chatgpt", "claude", "claude_code", "cursor", "gemini", "codex"}
    if platform in ai_platforms or any(item in family for item in ai_platforms):
        return "ai_conversation"
    return None


def _validate_limit(max_record_bytes: int) -> None:
    if not isinstance(max_record_bytes, int) or isinstance(max_record_bytes, bool) or max_record_bytes <= 0:
        raise ValueError("max_record_bytes must be a positive integer")


def _iter_binary_lines(stream, first_chunk: bytes, max_record_bytes: int):
    """Yield bounded binary JSONL lines, including a final unterminated line."""
    pending = bytearray()
    line_number = 0
    chunk = first_chunk
    while True:
        if not chunk:
            break
        start = 0
        while True:
            newline = chunk.find(b"\n", start)
            if newline < 0:
                part = chunk[start:]
                if len(pending) + len(part) > max_record_bytes:
                    raise ValueError(f"UPAR record exceeds limit at line {line_number + 1}")
                pending.extend(part)
                break
            part = chunk[start:newline + 1]
            if len(pending) + len(part) > max_record_bytes:
                raise ValueError(f"UPAR record exceeds limit at line {line_number + 1}")
            pending.extend(part)
            line_number += 1
            yield line_number, bytes(pending)
            pending.clear()
            start = newline + 1
            if start == len(chunk):
                break
        chunk = stream.read(_READ_CHUNK_BYTES)
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise TypeError("UPAR binary stream must return bytes")
        chunk = bytes(chunk)
    if pending:
        line_number += 1
        yield line_number, bytes(pending)


def _iter_text_lines(stream, first_chunk: str, max_record_bytes: int):
    """Yield bounded text JSONL lines for callers providing a text stream."""
    pending: list[str] = []
    pending_bytes = 0
    line_number = 0
    chunk = first_chunk
    while True:
        if not chunk:
            break
        start = 0
        while True:
            newline = chunk.find("\n", start)
            end = len(chunk) if newline < 0 else newline + 1
            part = chunk[start:end]
            part_bytes = len(part.encode("utf-8"))
            if pending_bytes + part_bytes > max_record_bytes:
                raise ValueError(f"UPAR record exceeds limit at line {line_number + 1}")
            pending.append(part)
            pending_bytes += part_bytes
            if newline < 0:
                break
            line_number += 1
            yield line_number, "".join(pending)
            pending.clear()
            pending_bytes = 0
            start = end
            if start == len(chunk):
                break
        chunk = stream.read(_READ_CHUNK_BYTES)
        if not isinstance(chunk, str):
            raise TypeError("UPAR text stream must return strings")
    if pending:
        line_number += 1
        yield line_number, "".join(pending)


def _iter_bounded_lines(stream, max_record_bytes: int):
    """Read JSONL in fixed-size chunks before any record-sized allocation."""
    _validate_limit(max_record_bytes)
    first_chunk = stream.read(_READ_CHUNK_BYTES)
    if isinstance(first_chunk, str):
        yield from _iter_text_lines(stream, first_chunk, max_record_bytes)
    elif isinstance(first_chunk, (bytes, bytearray, memoryview)):
        yield from _iter_binary_lines(stream, bytes(first_chunk), max_record_bytes)
    else:
        raise TypeError("UPAR stream must return bytes or strings")


def _iter_jsonl_records(stream, max_record_bytes: int):
    for line_number, line in _iter_bounded_lines(stream, max_record_bytes):
        if isinstance(line, bytes):
            try:
                line = line.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"UPAR record is not UTF-8 at line {line_number}") from exc
        if not line.strip():
            continue
        yield line_number, json.loads(line)


def iter_upar(stream: TextIO, *, domain: str | None = None,
              max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> Iterable[dict]:
    """Yield private source-preserving records from a UPAR JSONL stream.

    ``domain`` may be ``discord`` or ``ai_conversation``.  Unknown records are
    skipped only when a domain filter excludes them; malformed or oversized
    records raise with the line number so the caller can quarantine the file.
    """
    if domain not in (None, "discord", "ai_conversation"):
        raise ValueError("unsupported UPAR domain")
    for line_number, record in _iter_jsonl_records(stream, max_record_bytes):
        if not isinstance(record, dict):
            raise ValueError(f"UPAR record is not an object at line {line_number}")
        if record.get("kind") != "conversation":
            continue
        record_domain = _domain(record)
        if domain is not None and record_domain != domain:
            continue
        messages = record.get("messages")
        if not isinstance(messages, list):
            raise ValueError(f"conversation has no messages at line {line_number}")
        yield {"line": line_number, "domain": record_domain, "record": record}


def iter_upar_events(stream: TextIO, *, domain: str | None = None,
                     max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> Iterable[dict]:
    """Flatten UPAR conversations while preserving order and parent links."""
    for item in iter_upar(stream, domain=domain, max_record_bytes=max_record_bytes):
        record, record_domain = item["record"], item["domain"]
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        conversation_id = str(record.get("id") or record.get("content_hash") or
                              f"line:{item['line']}")
        for ordinal, message in enumerate(record["messages"], 1):
            if not isinstance(message, dict):
                raise ValueError(f"message is not an object at line {item['line']}")
            author = message.get("author") if isinstance(message.get("author"), dict) else {}
            role = str(message.get("role") or author.get("role") or "unknown")
            yield {
                "provider": record_domain or "unknown",
                "kind": "message",
                "conversation": conversation_id,
                "native_id": str(message.get("id") or message.get("uuid") or
                                    f"{conversation_id}:{ordinal}"),
                "ordinal": ordinal,
                "actor": author,
                "role": role,
                "content": _content(message.get("content", "")),
                "timestamp": message.get("timestamp") or record.get("time"),
                "parent_ids": [str(message["parent_id"])] if message.get("parent_id") else [],
                "extra": {"source": source, "record_type": record.get("type")},
            }


def iter_upar_path(path: str | Path, *, domain: str | None = None,
                   max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> Iterable[dict]:
    path = Path(path)
    with path.open("rb", buffering=_READ_CHUNK_BYTES) as stream:
        yield from iter_upar_events(stream, domain=domain, max_record_bytes=max_record_bytes)


def iter_upar_contract(stream: TextIO, *, domain: str | None = None,
                       max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> Iterable[dict]:
    """Adapt UPAR events to the contract-v1 records consumed by ``ingest``."""
    for position, event in enumerate(
            iter_upar_events(stream, domain=domain, max_record_bytes=max_record_bytes), 1):
        yield {"position": position, "status": "accepted", "reason": "accepted", "event": event}
