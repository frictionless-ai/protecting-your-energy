#!/usr/bin/env python3
"""Count session-pattern signals in the UPAR assistant corpus.

Writes counts only. Never writes message text. Default platforms are the
agent hosts. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hooks.session_signals import detect  # noqa: E402

DEFAULT_PLATFORMS = (
    "cursor",
    "claude_code",
    "copilot",
    "codex",
    "chatgpt",
)
AI_TYPES = {"assistant.session", "assistant.prompt_history"}
USER_ROLES = {"user", "self"}


def _content(msg: dict) -> str:
    raw = msg.get("content")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return " ".join(parts)
    return ""


def _role(msg: dict) -> str:
    role = (msg.get("role") or "").lower()
    if role:
        return role
    author = msg.get("author") or {}
    if isinstance(author, dict):
        return str(author.get("role") or "").lower()
    return ""


def iter_markdown_user_turns(root: Path):
    """Counts-only: user-turn bodies from consolidated session markdown."""
    sessions = root / "ai-conversations" / "sessions"
    if not sessions.is_dir():
        return
    for path in sorted(sessions.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "## User turns" not in text:
            continue
        body = text.split("## User turns", 1)[1]
        for chunk in body.split("### "):
            chunk = chunk.strip()
            if not chunk:
                continue
            # Drop the heading line; keep the user body until the next section.
            lines = chunk.splitlines()
            if len(lines) < 2:
                continue
            turn = "\n".join(lines[1:]).split("\n## ", 1)[0].strip()
            if turn:
                yield turn


def iter_records(root: Path, platforms: tuple[str, ...]):
    base = root / "archive" / "corpus" / "records" / "kind=conversation"
    for platform in platforms:
        d = base / f"platform={platform}"
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.jsonl")):
            with path.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield platform, rec


def mine(root: Path, platforms: tuple[str, ...], max_records: int) -> dict:
    sessions = 0
    user_turns = 0
    signal_counts: Counter[str] = Counter()
    pattern_sessions: Counter[str] = Counter()
    long_sessions = 0
    followup_after_signal = 0
    scanned = 0

    for _platform, rec in iter_records(root, platforms):
        if rec.get("kind") != "conversation":
            continue
        if rec.get("type") and rec.get("type") not in AI_TYPES:
            continue
        messages = rec.get("messages") or []
        if not messages:
            continue
        scanned += 1
        if max_records and scanned > max_records:
            break
        sessions += 1
        prev_user = ""
        session_signals: set[str] = set()
        n_user = 0
        for msg in messages:
            if _role(msg) not in USER_ROLES:
                continue
            text = _content(msg)
            if not text.strip():
                continue
            n_user += 1
            user_turns += 1
            found = detect(text, prev_user)
            for name in found:
                signal_counts[name] += 1
                session_signals.add(name)
            if prev_user and found:
                followup_after_signal += 1
            prev_user = text[:400]
        if n_user >= 8:
            long_sessions += 1
        for name in session_signals:
            pattern_sessions[name] += 1

    md_sessions = 0
    md_user_turns = 0
    sessions_dir = root / "ai-conversations" / "sessions"
    if sessions_dir.is_dir():
        for _path in sessions_dir.glob("*.md"):
            md_sessions += 1
    for turn in iter_markdown_user_turns(root):
        md_user_turns += 1
        user_turns += 1
        found = detect(turn, "")
        for name in found:
            signal_counts[name] += 1
            pattern_sessions[name] += 1

    return {
        "schema": "session-pattern-counts.v1",
        "root_present": (root / "archive" / "corpus" / "records").is_dir(),
        "platforms": list(platforms),
        "records_scanned": scanned,
        "sessions": sessions,
        "user_turns": user_turns,
        "long_sessions_8plus_user_turns": long_sessions,
        "followup_with_signal": followup_after_signal,
        "signals": dict(signal_counts),
        "sessions_with_signal": dict(pattern_sessions),
        "markdown_sessions_scanned": md_sessions,
        "markdown_user_turns": md_user_turns,
        "raw_text_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.environ.get("THOUGHT_RECONSTRUCTION_ARCHIVE") or os.environ.get("PYE_ARCHIVE_ROOT"),
    )
    parser.add_argument("--out", default="")
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument(
        "--platforms",
        default=",".join(DEFAULT_PLATFORMS),
    )
    args = parser.parse_args()
    if not args.root:
        parser.error("--root or a configured archive environment is required")
    platforms = tuple(p.strip() for p in args.platforms.split(",") if p.strip())
    data = mine(Path(args.root), platforms, args.max_records)
    text = json.dumps(data, indent=2) + "\n"
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        print(dest)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
