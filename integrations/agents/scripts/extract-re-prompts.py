#!/usr/bin/env python3
"""Extract unique RE-related prompts from all agent CLI histories."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Import sibling module (hyphenated filename)
import runpy

_sph = runpy.run_path(str(Path(__file__).resolve().parent / "search-prompt-history.py"))
sph = type(sys)("sph")
for k, v in _sph.items():
    if not k.startswith("_"):
        setattr(sph, k, v)

PATTERN = re.compile(
    r"agentdecompile|swkotor|mizuchi|reconkit|decompil|reverse.?engineer|objdiff|ghidra|roundtrip|one.?shot|matching.?decomp|bytecode|macabeus|puzzle.?piece|context.?pack",
    re.I,
)

SKIP = re.compile(r"^/[a-z-]+$", re.I)


def main() -> int:
    matches = []
    seen: set[str] = set()
    for source, path, kind in sph.discover_sources(sph.DEFAULT_SOURCES):
        for match in sph.iter_source(source, path, kind):
            text = match.text.strip()
            if not text or not PATTERN.search(text):
                continue
            if SKIP.match(text):
                continue
            key = sph.normalize_text(text)
            if key in seen:
                continue
            seen.add(key)
            matches.append(match.__dict__)

    out = Path(os.environ.get("PYE_HISTORY_OUTPUT", str(Path.home() / ".local/share/protecting-your-energy/history/re-prompts.json"))).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with out.open("w", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        handle.write(json.dumps(matches, indent=2, ensure_ascii=False))
    by_source: dict[str, int] = {}
    for m in matches:
        by_source[m["source"]] = by_source.get(m["source"], 0) + 1
    print(f"Unique RE prompts: {len(matches)}")
    print("By source:", by_source)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
