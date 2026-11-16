"""Stream selected UPAR conversations into a private evidence JSONL file.

This is intentionally a derived evidence view, not a release builder.  The
UPAR archive remains the immutable source; the output retains raw message
content and provenance for later privacy/fidelity review and must stay private.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path
import tempfile
from .focus import discord_in_period

from .upar import DEFAULT_MAX_RECORD_BYTES, iter_upar


AI_PLATFORMS = {"chatgpt", "claude", "claude_code", "codex", "cursor", "gemini"}


def _platform(record: dict) -> str:
    source = record.get("source")
    return str(source.get("platform", "")).casefold() if isinstance(source, dict) else ""


def _parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _message_time(message: dict, record: dict):
    value = message.get("sent_at") or message.get("time") or message.get("timestamp")
    if value is None and isinstance(record.get("time"), str):
        value = record["time"]
    return _parse_time(value)


def _in_discord_window(message: dict, record: dict) -> bool:
    value = _message_time(message, record)
    return value is not None and discord_in_period(value.isoformat())


def iter_selected(root: str | Path, *, domain: str | None = None,
                  max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES):
    """Yield selected near-raw records without loading a shard into memory."""
    root = Path(root)
    for path in sorted(root.glob("kind=conversation/**/*.jsonl")):
        platform_hint = path.parts[-2].split("=", 1)[-1] if len(path.parts) >= 2 else ""
        if domain == "discord" and platform_hint != "discord":
            continue
        if domain == "ai_conversation" and platform_hint not in AI_PLATFORMS:
            continue
        with path.open("rb", buffering=256 * 1024) as stream:
            for item in iter_upar(stream, domain=domain, max_record_bytes=max_record_bytes):
                record = item["record"]
                platform = _platform(record)
                if platform == "discord":
                    messages = [
                        dict(message, _upar_source_ordinal=ordinal)
                        for ordinal, message in enumerate(record.get("messages", []))
                        if isinstance(message, dict) and _in_discord_window(message, record)
                    ]
                    if not messages:
                        continue
                    record = dict(record, messages=messages)
                elif platform not in AI_PLATFORMS:
                    continue
                yield {"source_file": str(path), "source_line": item["line"],
                       "record": record}


def extract(root: str | Path, output: str | Path, *, domain: str | None = None,
            max_record_bytes: int = DEFAULT_MAX_RECORD_BYTES) -> dict:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    summary_path = output.with_suffix(".summary.json")
    output_temp = summary_temp = None
    count = messages = 0
    digest = hashlib.sha256()
    try:
        output_fd, output_name = tempfile.mkstemp(
            prefix=f".{output.name}.", suffix=".partial", dir=output.parent)
        output_temp = Path(output_name)
        with os.fdopen(output_fd, "w", encoding="utf-8", newline="\n") as sink:
            for item in iter_selected(root, domain=domain, max_record_bytes=max_record_bytes):
                line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                sink.write(line)
                digest.update(line.encode("utf-8"))
                count += 1
                messages += len(item["record"].get("messages", []))
            sink.flush()
            os.fsync(sink.fileno())
        report = {"status": "terminal", "domain": domain, "records": count,
                  "messages": messages, "output": str(output), "terminal": True,
                  "output_sha256": digest.hexdigest()}
        summary_fd, summary_name = tempfile.mkstemp(
            prefix=f".{summary_path.name}.", suffix=".partial", dir=summary_path.parent)
        summary_temp = Path(summary_name)
        with os.fdopen(summary_fd, "w", encoding="utf-8", newline="\n") as sink:
            sink.write(json.dumps(report, indent=2) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
        os.replace(output_temp, output)
        output_temp = None
        os.replace(summary_temp, summary_path)
        summary_temp = None
        return report
    finally:
        for path in (output_temp, summary_temp):
            if path is not None:
                path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--domain", choices=("discord", "ai_conversation"))
    parser.add_argument("--max-record-bytes", type=int, default=DEFAULT_MAX_RECORD_BYTES)
    args = parser.parse_args()
    print(json.dumps(extract(args.root, args.output, domain=args.domain,
                             max_record_bytes=args.max_record_bytes)))


if __name__ == "__main__":
    main()
