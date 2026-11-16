#!/usr/bin/env python3
"""Validate a live scorecard and optionally save an explicitly requested private record."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

REQUIRED = ("id", "source", "executor", "consulted_skill", "route", "gaps",
            "contract", "compiled_prompt", "isolation", "pass", "fail_reasons")


def validate(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("scorecard must be an object")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError(f"missing keys: {missing}")
    case_id = data["id"]
    if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", case_id) or ".." in case_id:
        raise ValueError("id must be a bounded filename-safe case identifier")
    if data["source"] != "live-skill":
        raise ValueError('source must be "live-skill"')
    if data["executor"] not in ("self", "fork") or data["route"] not in ("uplift", "pass"):
        raise ValueError("invalid executor or route")
    if type(data["consulted_skill"]) is not bool or type(data["pass"]) is not bool:
        raise ValueError("consulted_skill and pass must be booleans")
    if not isinstance(data["contract"], dict) or not isinstance(data["compiled_prompt"], str):
        raise ValueError("contract must be an object and compiled_prompt a string")
    for key in ("gaps", "fail_reasons"):
        if not isinstance(data[key], list) or not all(isinstance(item, str) for item in data[key]):
            raise ValueError(f"{key} must be a list of strings")
    isolation = data["isolation"]
    if not isinstance(isolation, dict) or any(
        type(isolation.get(key)) is not bool
        for key in ("engineer_saw_conversation", "engineer_saw_raw_message")
    ):
        raise ValueError("isolation must explicitly record both boolean observations")
    return data


def digest(value: object) -> dict:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {"redacted": True, "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def stored_record(data: dict, include_text: bool = False) -> dict:
    record = {key: data[key] for key in REQUIRED}
    record["text_retained"] = include_text
    if include_text:
        for key in ("klass", "target_model", "ab"):
            if key in data:
                record[key] = data[key]
    else:
        for key in ("contract", "compiled_prompt", "gaps", "fail_reasons"):
            record[key] = digest(data[key])
        if "ab" in data:
            record["ab"] = digest(data["ab"])
    return record


def output_root() -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    return Path(os.environ.get("PROMPT_UPLIFT_LIVE_RUNS") or state / "protecting-your-energy/prompt-uplift/live-runs").expanduser()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write one private record; otherwise validate only")
    parser.add_argument("--out-dir", type=Path, help="Explicit private destination, overriding PROMPT_UPLIFT_LIVE_RUNS/XDG state")
    parser.add_argument("--include-text", action="store_true", help="Explicitly retain contract, prompt and reasoning text in the private record")
    args = parser.parse_args()
    try:
        data = validate(json.load(sys.stdin))
        record = stored_record(data, args.include_text)
        if not args.write:
            print(json.dumps({"valid": True, "written": False, "id": data["id"]}))
            return 0
        root = (args.out_dir or output_root()).expanduser()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / (data["id"] + ".json")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        print(json.dumps({"valid": True, "written": True, "path": str(path)}))
        return 0
    except (ValueError, OSError, RecursionError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
