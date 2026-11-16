"""JSON-RPC stdio framing for MCP.

Cursor speaks LSP-style Content-Length frames. A body is not newline-terminated.
The previous server used readline() on NDJSON, so initialize hung until the
client proxy timed out (~30s, MCP -32001).
"""
from __future__ import annotations

import json
from typing import Any, BinaryIO, TextIO


def read_message(stream: BinaryIO) -> dict | None:
    """Read one JSON-RPC message. Accepts Content-Length frames or a JSON line."""
    first = stream.readline()
    if not first:
        return None
    stripped = first.lstrip()
    if stripped.startswith(b"{") or stripped.startswith(b"["):
        return json.loads(stripped)
    headers: dict[str, str] = {}
    line = first
    while True:
        if line in (b"\r\n", b"\n", b""):
            if line == b"":
                return None
            break
        if b":" in line:
            key, val = line.split(b":", 1)
            headers[key.decode("ascii", errors="replace").strip().lower()] = (
                val.decode("ascii", errors="replace").strip()
            )
        line = stream.readline()
        if line == b"":
            return None
    n = int(headers.get("content-length") or 0)
    if n <= 0:
        return None
    body = stream.read(n)
    if len(body) < n:
        return None
    return json.loads(body)


def write_message(stream: BinaryIO, obj: dict[str, Any]) -> None:
    data = json.dumps(obj, default=str).encode("utf-8")
    stream.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii"))
    stream.write(data)
    stream.flush()


def write_message_text(stream: TextIO, obj: dict[str, Any]) -> None:
    write_message(stream.buffer, obj)
