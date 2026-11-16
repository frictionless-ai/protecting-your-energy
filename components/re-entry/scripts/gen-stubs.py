#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / ".agents" / "skills"
TARGETS = [ROOT / "skills", ROOT / ".claude" / "skills", ROOT / ".cursor" / "skills"]


def frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[: i + 1])
    raise ValueError("unterminated frontmatter")


def stub(name: str, canon: Path, target_dir: Path, fm: str) -> str:
    rel = os.path.relpath(canon, target_dir).replace(os.sep, "/")
    return (
        f"{fm}\n# {name}\n\n"
        f"Canonical skill: [{rel}]({rel})\n\n"
        "Read that file and follow it. Do not continue from this stub.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    check = ap.parse_args().check

    if not CANON.is_dir():
        print(f"missing canonical skills: {CANON}", file=sys.stderr)
        return 1

    names = sorted(p.parent.name for p in CANON.glob("*/SKILL.md"))
    bad = False
    for base in TARGETS:
        for name in names:
            canon = CANON / name / "SKILL.md"
            out_dir = base / name
            want = stub(name, canon, out_dir, frontmatter(canon.read_text(encoding="utf-8")))
            out = out_dir / "SKILL.md"
            if out.exists() and out.read_text(encoding="utf-8") == want:
                continue
            bad = True
            if check:
                print(f"stale: {out.relative_to(ROOT)}", file=sys.stderr)
            else:
                out_dir.mkdir(parents=True, exist_ok=True)
                out.write_text(want, encoding="utf-8")
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name not in names:
                    bad = True
                    if check:
                        print(f"orphan: {d.relative_to(ROOT)}", file=sys.stderr)
                    else:
                        shutil.rmtree(d)
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
