#!/usr/bin/env python3
"""Search up/down prompt history across AI agent CLIs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from glob import iglob
from pathlib import Path
from typing import Iterable, Iterator


@dataclass
class HistoryMatch:
    source: str
    path: str
    line: int | None
    index: int | None
    timestamp: str | None
    session_id: str | None
    project: str | None
    text: str


DEFAULT_SOURCES = (
    "codex",
    "claude",
    "cursor",
    "grok",
    "copilot",
    "gemini",
)


def expand(path: str) -> str:
    return os.path.expanduser(path)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def iter_codex(path: Path) -> Iterator[HistoryMatch]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = entry.get("text")
            if not isinstance(text, str):
                continue
            ts = entry.get("ts")
            timestamp = None
            if isinstance(ts, (int, float)):
                timestamp = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            yield HistoryMatch(
                source="codex",
                path=str(path),
                line=line_no,
                index=None,
                timestamp=timestamp,
                session_id=entry.get("session_id"),
                project=None,
                text=text,
            )


def iter_claude(path: Path) -> Iterator[HistoryMatch]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = entry.get("display")
            if not isinstance(text, str):
                continue
            ts = entry.get("timestamp")
            timestamp = None
            if isinstance(ts, (int, float)):
                timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
            yield HistoryMatch(
                source="claude",
                path=str(path),
                line=line_no,
                index=None,
                timestamp=timestamp,
                session_id=entry.get("sessionId"),
                project=entry.get("project"),
                text=text,
            )


def iter_json_string_array(path: Path, source: str) -> Iterator[HistoryMatch]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(payload, list):
        return
    for index, item in enumerate(payload, 1):
        if not isinstance(item, str):
            continue
        yield HistoryMatch(
            source=source,
            path=str(path),
            line=None,
            index=index,
            timestamp=None,
            session_id=None,
            project=None,
            text=item,
        )


def iter_grok(path: Path) -> Iterator[HistoryMatch]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = entry.get("prompt")
            if not isinstance(text, str):
                continue
            yield HistoryMatch(
                source="grok",
                path=str(path),
                line=line_no,
                index=None,
                timestamp=entry.get("timestamp"),
                session_id=entry.get("session_id"),
                project=path.parent.name,
                text=text,
            )


def iter_copilot_command_history(path: Path) -> Iterator[HistoryMatch]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return
    commands = payload.get("commandHistory")
    if not isinstance(commands, list):
        return
    for index, text in enumerate(commands, 1):
        if not isinstance(text, str):
            continue
        yield HistoryMatch(
            source="copilot",
            path=str(path),
            line=None,
            index=index,
            timestamp=None,
            session_id=None,
            project=None,
            text=text,
        )


def iter_copilot_sessions(path: Path) -> Iterator[HistoryMatch]:
    if not path.is_file():
        return
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT t.turn_index, t.user_message, t.timestamp, t.session_id
            FROM turns t
            WHERE t.user_message IS NOT NULL AND TRIM(t.user_message) != ''
            ORDER BY t.id
            """
        )
        for turn_index, user_message, timestamp, session_id in rows:
            yield HistoryMatch(
                source="copilot",
                path=str(path),
                line=None,
                index=turn_index,
                timestamp=timestamp,
                session_id=session_id,
                project="session-store.db",
                text=user_message,
            )
    finally:
        conn.close()


def extract_gemini_user_text(entry: dict) -> list[str]:
    texts: list[str] = []
    messages = entry.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict) or message.get("type") != "user":
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    texts.append(block["text"])
    update = entry.get("update")
    if isinstance(update, dict):
        for key in ("userMessage", "prompt", "text"):
            value = update.get(key)
            if isinstance(value, str):
                texts.append(value)
    for key in ("prompt", "text", "message"):
        value = entry.get(key)
        if isinstance(value, str):
            texts.append(value)
    return texts


def iter_gemini(path: Path) -> Iterator[HistoryMatch]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            payload = entry.get("$set", entry)
            if not isinstance(payload, dict):
                continue
            for text in extract_gemini_user_text(payload):
                if "<session_context>" in text and "Gemini CLI" in text:
                    continue
                yield HistoryMatch(
                    source="gemini",
                    path=str(path),
                    line=line_no,
                    index=None,
                    timestamp=payload.get("lastUpdated") or entry.get("startTime"),
                    session_id=payload.get("sessionId") or entry.get("sessionId"),
                    project=path.parent.parent.name,
                    text=text,
                )


def discover_sources(selected: Iterable[str]) -> list[tuple[str, Path, str]]:
    home = Path.home()
    selected_set = set(selected)
    discovered: list[tuple[str, Path, str]] = []

    def add(source: str, path: Path, kind: str) -> None:
        if source in selected_set:
            discovered.append((source, path, kind))

    codex_home = Path(expand(os.environ.get("CODEX_HOME", "~/.codex")))
    add("codex", codex_home / "history.jsonl", "codex")
    add("claude", home / ".claude" / "history.jsonl", "claude")
    add("cursor", home / ".config" / "cursor" / "prompt_history.json", "cursor_array")
    for path in iglob(str(home / ".cursor" / "chats" / "*" / "*" / "prompt_history.json")):
        add("cursor", Path(path), "cursor_array")
    for path in iglob(str(home / ".grok" / "sessions" / "**" / "prompt_history.jsonl"), recursive=True):
        add("grok", Path(path), "grok")
    add("copilot", home / ".copilot" / "command-history-state.json", "copilot_commands")
    add("copilot", home / ".copilot" / "session-store.db", "copilot_db")
    for path in iglob(str(home / ".gemini" / "tmp" / "**" / "chats" / "*.jsonl"), recursive=True):
        add("gemini", Path(path), "gemini")

    return discovered


def iter_source(source: str, path: Path, kind: str) -> Iterator[HistoryMatch]:
    if not path.exists():
        return
    if kind == "codex":
        yield from iter_codex(path)
    elif kind == "claude":
        yield from iter_claude(path)
    elif kind == "cursor_array":
        yield from iter_json_string_array(path, "cursor")
    elif kind == "grok":
        yield from iter_grok(path)
    elif kind == "copilot_commands":
        yield from iter_copilot_command_history(path)
    elif kind == "copilot_db":
        yield from iter_copilot_sessions(path)
    elif kind == "gemini":
        yield from iter_gemini(path)
    else:
        raise ValueError(f"Unknown source kind: {source}:{kind}")


def search_all(
    phrase: str,
    *,
    sources: Iterable[str],
    case_insensitive: bool = True,
    limit: int = 20,
) -> list[HistoryMatch]:
    needle = phrase.lower() if case_insensitive else phrase
    matches: list[HistoryMatch] = []
    seen: set[tuple[str, str]] = set()

    for source, path, kind in discover_sources(sources):
        for match in iter_source(source, path, kind):
            haystack = match.text.lower() if case_insensitive else match.text
            if needle not in haystack:
                continue
            key = (source, normalize_text(match.text))
            if key in seen:
                continue
            seen.add(key)
            matches.append(match)

    if limit <= 0:
        return matches
    return matches[-limit:]


def format_match(index: int, match: HistoryMatch) -> str:
    location = []
    if match.line is not None:
        location.append(f"line {match.line}")
    if match.index is not None:
        location.append(f"index {match.index}")
    location_text = ", ".join(location) if location else "n/a"
    lines = [
        f"--- Match {index} [{match.source}] ({location_text}) ---",
        f"path: {match.path}",
    ]
    if match.timestamp:
        lines.append(f"timestamp: {match.timestamp}")
    if match.session_id:
        lines.append(f"session_id: {match.session_id}")
    if match.project:
        lines.append(f"project: {match.project}")
    lines.extend(["", match.text])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search prompt history across Codex, Claude, Cursor, Grok, Copilot, and Gemini CLIs"
    )
    parser.add_argument("phrase", nargs="?", help="Substring to search for")
    parser.add_argument(
        "--sources",
        default=",".join(DEFAULT_SOURCES),
        help=f"Comma-separated sources (default: {','.join(DEFAULT_SOURCES)})",
    )
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--limit", type=int, default=20, help="Max unique matches (most recent)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--list-sources", action="store_true", help="List discovered history files")
    args = parser.parse_args()

    selected = [part.strip() for part in args.sources.split(",") if part.strip()]
    if args.list_sources:
        for source, path, kind in discover_sources(selected):
            print(f"{source:8} {kind:16} {path}")
        return 0

    if not args.phrase:
        parser.error("phrase is required unless --list-sources is used")

    matches = search_all(
        args.phrase,
        sources=selected,
        case_insensitive=not args.case_sensitive,
        limit=args.limit,
    )

    if args.json:
        print(
            json.dumps(
                [match.__dict__ for match in matches],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        if not matches:
            print(f"No matches for: {args.phrase!r}")
        else:
            print(
                "\n\n".join(
                    format_match(index, match)
                    for index, match in enumerate(matches, 1)
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
