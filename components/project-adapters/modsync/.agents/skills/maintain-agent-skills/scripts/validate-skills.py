#!/usr/bin/env python3
"""Validate Agent Skills under .agents/skills/ (agentskills.io specification)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESC = 1024
MAX_COMPAT = 500
MAX_SKILL_LINES = 500


def usage() -> str:
    return """Usage: python3 scripts/validate-skills.py [--root DIR] [--strict]

Validate SKILL.md frontmatter and layout for every skill under .agents/skills/.

Options:
  --root DIR   Repo root (default: walk up from this script to find .agents/skills)
  --strict     Treat warnings (body > 500 lines) as errors
  --help       Show this help

Exit codes:
  0  all skills valid
  2  one or more errors
  3  invalid arguments
"""


def parse_frontmatter(text: str) -> tuple[dict[str, str], str] | tuple[None, str]:
    if not text.startswith("---"):
        return None, "SKILL.md must start with YAML frontmatter (---)"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "SKILL.md frontmatter is not closed with ---"
    raw = parts[1]
    body = parts[2]
    data: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal key, buf
        if key is None:
            return
        data[key] = "\n".join(buf).strip()
        key = None
        buf = []

    for line in raw.splitlines():
        if not line.strip():
            if key:
                buf.append("")
            continue
        if line.startswith("  ") and key:
            buf.append(line.strip().lstrip(">").strip())
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            flush()
            key = m.group(1)
            rest = m.group(2)
            if rest in (">", "|"):
                buf = []
            else:
                buf = [rest.strip().strip('"').strip("'")]
            continue
        if key:
            buf.append(line.strip())
    flush()
    return data, body


def find_repo_root(explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".agents" / "skills").is_dir():
            return parent
    return Path.cwd()


def validate_skill(skill_dir: Path, strict: bool) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    parsed = parse_frontmatter(text)
    if parsed[0] is None:
        return [f"{skill_dir.name}: {parsed[1]}"]
    data, body = parsed
    name = data.get("name", "")
    desc = re.sub(r"\s+", " ", data.get("description", "")).strip()
    dirname = skill_dir.name
    if dirname.startswith("_"):
        return []
    if name != dirname:
        errors.append(f"{dirname}: name '{name}' does not match directory")
    if not name or len(name) > MAX_NAME or not NAME_RE.match(name):
        errors.append(
            f"{dirname}: name must be 1-{MAX_NAME} chars, lowercase, digits, hyphens "
            "(no leading/trailing/consecutive hyphens)"
        )
    if not desc:
        errors.append(f"{dirname}: description is required")
    elif len(desc) > MAX_DESC:
        errors.append(f"{dirname}: description is {len(desc)} chars (max {MAX_DESC})")
    compat = data.get("compatibility", "").strip()
    if compat and len(compat) > MAX_COMPAT:
        errors.append(f"{dirname}: compatibility is {len(compat)} chars (max {MAX_COMPAT})")
    line_count = body.count("\n") + (0 if body.endswith("\n") or not body else 1)
    if line_count > MAX_SKILL_LINES:
        msg = f"{dirname}: SKILL.md body is {line_count} lines (spec recommends < {MAX_SKILL_LINES})"
        if strict:
            errors.append(msg)
        else:
            print(f"warning: {msg}", file=sys.stderr)
    for ref in skill_dir.glob("references/**/*"):
        if ref.is_file() and ref.suffix == ".md":
            rel = ref.relative_to(skill_dir)
            if len(rel.parts) > 2:
                errors.append(f"{dirname}: nested reference {rel} (keep one level from SKILL.md)")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--help", action="store_true")
    args = parser.parse_args(argv)
    if args.help:
        print(usage())
        return 0
    root = find_repo_root(args.root)
    skills_root = root / ".agents" / "skills"
    if not skills_root.is_dir():
        print(f"Error: {skills_root} not found. Pass --root <repo>.", file=sys.stderr)
        return 3
    errors: list[str] = []
    skills = sorted(p for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").exists())
    if not skills:
        print(f"Error: no skills under {skills_root}", file=sys.stderr)
        return 2
    for skill_dir in skills:
        errors.extend(validate_skill(skill_dir, args.strict))
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"Error: {len(errors)} validation failure(s).", file=sys.stderr)
        return 2
    print(f'{{"ok": true, "skills": {len(skills)}, "root": "{skills_root}"}}')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
