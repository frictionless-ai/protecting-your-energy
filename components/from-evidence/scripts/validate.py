#!/usr/bin/env python3
"""Validate the plugin structure, datasets and build manifest.

Usage:
    python3 scripts/validate.py

Mirrors what `claude plugin validate` checks (manifest JSON, kebab name,
skill and agent frontmatter, hooks JSON) and adds this plugin's own
contracts: every dataset under datasets/ and every entry in build.json.
Exit 0 when clean, 1 when anything fails. Standard library only.
"""

from __future__ import annotations

import json
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    BUILD_JSON,
    DATASETS,
    KEBAB,
    PLUGIN_JSON,
    ROOT,
    SEMVER,
    TEMPLATES,
    ContractError,
    parse_frontmatter,
    read_json,
    validate_dataset,
)

AGENT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")
MAX_SKILL_WORDS = 3000
BUZZWORDS = ("seamless", "robust", "powerful", "unified", "holistic", "leverage", "cutting-edge")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def check_manifest() -> None:
    if not PLUGIN_JSON.is_file():
        err(".claude-plugin/plugin.json missing")
        return
    try:
        m = read_json(PLUGIN_JSON)
    except ContractError as exc:
        err(str(exc))
        return
    name = m.get("name")
    if not isinstance(name, str) or not KEBAB.match(name):
        err(".claude-plugin/plugin.json: name must be kebab-case")
    if "version" in m and not SEMVER.match(str(m["version"])):
        err(".claude-plugin/plugin.json: version must be semver")
    if "repository" in m and ("TBD" in str(m["repository"]) or "placeholder" in str(m["repository"]).lower()):
        err(".claude-plugin/plugin.json: repository must be a real URL or absent")
    for key in ("commands", "agents", "hooks", "mcpServers"):
        if key in m:
            paths = m[key] if isinstance(m[key], list) else [m[key]]
            for p in paths:
                if not (ROOT / p).exists():
                    err(f".claude-plugin/plugin.json: {key} path '{p}' does not exist")


def word_count(body: str) -> int:
    return len(body.split())


def check_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        err("skills/ missing")
        return
    dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    if not dirs:
        err("skills/: no skill directories")
    for d in dirs:
        skill = d / "SKILL.md"
        if not skill.is_file():
            err(f"skills/{d.name}: no SKILL.md")
            continue
        text = skill.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            err(f"skills/{d.name}/SKILL.md: no YAML frontmatter")
            continue
        if fm.get("name") != d.name:
            err(f"skills/{d.name}/SKILL.md: frontmatter name '{fm.get('name')}' must equal directory name")
        desc = fm.get("description", "")
        if not desc:
            err(f"skills/{d.name}/SKILL.md: description missing")
        elif '"' not in desc:
            warn(f"skills/{d.name}/SKILL.md: description has no quoted trigger phrase")
        elif re.match(r"^(I |You )", desc):
            err(f"skills/{d.name}/SKILL.md: description must be third person")
        body = text.split("\n---", 2)[-1]
        wc = word_count(body)
        if wc > MAX_SKILL_WORDS:
            err(f"skills/{d.name}/SKILL.md: body is {wc} words (max {MAX_SKILL_WORDS})")
        low = body.lower()
        hits = [b for b in BUZZWORDS if re.search(rf"\b{re.escape(b)}\b", low)]
        if hits:
            err(f"skills/{d.name}/SKILL.md: buzzwords {hits}")
        for link in re.findall(r"\]\((references/[^)]+)\)", body):
            if not (d / link).is_file():
                err(f"skills/{d.name}/SKILL.md: broken link {link}")
        for ref in re.findall(r"`(references/[a-z0-9_./-]+\.md)`", body):
            if not (d / ref).is_file():
                err(f"skills/{d.name}/SKILL.md: missing {ref}")


def check_agents() -> None:
    agents_dir = ROOT / "agents"
    if not agents_dir.is_dir():
        return
    for f in sorted(agents_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            err(f"agents/{f.name}: no YAML frontmatter")
            continue
        name = fm.get("name", "")
        if not AGENT_NAME.match(name):
            err(f"agents/{f.name}: name '{name}' must be 3-50 chars, lowercase, hyphens")
        if name != f.stem:
            err(f"agents/{f.name}: name '{name}' must equal file stem")
        desc = fm.get("description", "")
        if not desc:
            err(f"agents/{f.name}: description missing")
        elif "<example>" not in desc:
            err(f"agents/{f.name}: description has no <example> block")
        if fm.get("model") not in ("inherit", "sonnet", "opus", "haiku"):
            err(f"agents/{f.name}: model must be inherit|sonnet|opus|haiku")
        if fm.get("color") not in ("blue", "cyan", "green", "yellow", "magenta", "red"):
            err(f"agents/{f.name}: color must be one of blue cyan green yellow magenta red")
        body = text.split("\n---", 2)[-1].strip()
        if len(body) < 200:
            err(f"agents/{f.name}: system prompt body is too short")


def check_hooks() -> None:
    hooks = ROOT / "hooks" / "hooks.json"
    if hooks.is_file():
        try:
            read_json(hooks)
        except ContractError as exc:
            err(str(exc))
    tpl = TEMPLATES / "hooks.json"
    if tpl.is_file():
        # Placeholders make it non-JSON on purpose; check the braces still balance.
        text = tpl.read_text(encoding="utf-8")
        if text.count("{") != text.count("}"):
            err("templates/hooks.json: unbalanced braces")


def check_datasets() -> None:
    if not DATASETS.is_dir():
        err("datasets/ missing")
        return
    found = False
    for d in sorted(p for p in DATASETS.iterdir() if p.is_dir()):
        found = True
        try:
            validate_dataset(d)
        except ContractError as exc:
            err(str(exc))
    if not found:
        err("datasets/: no dataset directories")


def check_build_manifest() -> None:
    if not BUILD_JSON.is_file():
        err("build.json missing")
        return
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import build  # noqa: WPS433

        build.load_manifest()
    except ContractError as exc:
        err(str(exc))
    except json.JSONDecodeError as exc:
        err(f"build.json: invalid JSON ({exc.msg})")


def check_templates() -> None:
    for name in ("SKILL.md", "reference.md", "EVOLUTION.md", "rule.md", "agent.md", "hooks.json", "DESIGN.md"):
        if not (TEMPLATES / name).is_file():
            err(f"templates/{name} missing")
    for provider in ("codex", "cursor", "gemini", "copilot", "opencode"):
        d = TEMPLATES / "providers" / provider
        if not d.is_dir() or not any(p.is_file() for p in d.rglob("*")):
            err(f"templates/providers/{provider}: missing or empty")


def check_gitignore() -> None:
    gi = ROOT / ".gitignore"
    if not gi.is_file():
        err(".gitignore missing")
        return
    text = gi.read_text(encoding="utf-8")
    if "generated/*" not in text or "!generated/.gitkeep" not in text:
        err(".gitignore must contain 'generated/*' and '!generated/.gitkeep'")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', action='store_true',
                        help='Also validate the configured private datasets and build plan')
    args = parser.parse_args()
    for check in (
        check_manifest,
        check_skills,
        check_agents,
        check_hooks,
        check_templates,
        check_gitignore,
    ):
        check()
    if args.workspace:
        check_datasets()
        check_build_manifest()
    for w in warnings:
        print(f"[validate] warning: {w}")
    for e in errors:
        print(f"[validate] error: {e}")
    skills = len([p for p in (ROOT / "skills").iterdir() if p.is_dir()]) if (ROOT / "skills").is_dir() else 0
    agents = len(list((ROOT / "agents").glob("*.md"))) if (ROOT / "agents").is_dir() else 0
    datasets = len([p for p in DATASETS.iterdir() if p.is_dir()]) if args.workspace and DATASETS.is_dir() else 0
    print(f"[validate] {skills} skills, {agents} agents, {datasets} datasets, "
          f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
