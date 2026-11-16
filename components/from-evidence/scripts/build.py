#!/usr/bin/env python3
"""Render generated skills from datasets and templates.

Usage:
    python3 scripts/build.py                # every entry in build.json
    python3 scripts/build.py --only NAME    # one generated skill
    python3 scripts/build.py --check        # validate inputs, render nothing

Deterministic: same inputs, byte-identical output. No timestamps.
Standard library only.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    BUILD_JSON,
    DATASETS,
    GENERATED,
    PLUGIN_JSON,
    QUOTABLE_QUALITY,
    ROOT,
    SUBJECT,
    TEMPLATES,
    ContractError,
    KEBAB,
    read_json,
    render,
    split_records,
    validate_dataset,
)

CANONICAL_TARGET = "claude"
PROVIDER_TARGETS = ("codex", "cursor", "gemini", "copilot", "opencode")
ALL_TARGETS = (CANONICAL_TARGET,) + PROVIDER_TARGETS
KINDS = {"skill", "subagent"}


def bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def anti_pattern_bullets(antis: list[dict]) -> str:
    out = []
    for a in antis:
        line = f"- Never {a['description']}."
        if a["markers"]:
            line += " Tell-tale phrases: " + ", ".join(f'"{m}"' for m in a["markers"]) + "."
        out.append(line)
    return "\n".join(out)


def phrase_bullets(phrases: list[dict]) -> str:
    out = []
    for p in phrases:
        cite = f"; {', '.join(p['ids'])}" if p["ids"] else ""
        out.append(f'- "{p["phrase"]}" (n={p["n"]}{cite})')
    return "\n".join(out)


def moves_table(training: list[dict]) -> str:
    counts = Counter(m for r in training for m in r["moves"])
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    lines = ["| Move | Count |", "|---|---|"]
    lines += [f"| `{m}` | {n} |" for m, n in rows]
    return "\n".join(lines)


def self_lines(training: list[dict]) -> str:
    out = []
    for r in training:
        if r["quality"] < QUOTABLE_QUALITY:
            continue
        for t in r["turns"]:
            if t["author"] == SUBJECT:
                out.append(f'- {r["id"]}: "{t["text"]}"')
    return "\n".join(out)


def exemplars(training: list[dict]) -> str:
    blocks = []
    for r in training:
        if r["quality"] < QUOTABLE_QUALITY:
            continue
        head = f"### {r['id']}: {r['topic']} ({r['partner']}, {r['outcome']}, quality {r['quality']})"
        turns = [f"- **{t['author']}**: {t['text']}" for t in r["turns"]]
        why = f"Why it worked or failed: {r['why_it_worked_or_failed']}"
        moves = "Moves: " + ", ".join(f"`{m}`" for m in r["moves"])
        blocks.append("\n".join([head, "", *turns, "", moves, "", why]))
    return "\n\n".join(blocks)


def inline_exemplars(training: list[dict], ids: list[str]) -> str:
    by_id = {r["id"]: r for r in training}
    blocks = []
    import re

    for spec_id in ids:
        m = re.match(r"^(r-\d{3,})(?::(\d+)-(\d+))?$", spec_id)
        if not m:
            raise ContractError(f"spec.md Inline exemplars: '{spec_id}' must be 'r-NNN' or 'r-NNN:lo-hi' (1-based turns)")
        rid = m.group(1)
        r = by_id.get(rid)
        if r is None:
            raise ContractError(f"spec.md Inline exemplars: '{rid}' is not a training record")
        if r["quality"] < QUOTABLE_QUALITY:
            raise ContractError(f"spec.md Inline exemplars: '{rid}' is quality {r['quality']}; only >= {QUOTABLE_QUALITY} is quotable")
        sel = r["turns"]
        if m.group(2):
            lo, hi = int(m.group(2)), int(m.group(3))
            if not (1 <= lo <= hi <= len(sel)):
                raise ContractError(f"spec.md Inline exemplars: '{spec_id}' range outside 1-{len(sel)}")
            sel = sel[lo - 1:hi]
        head = f"**{r['id']}: {r['topic']}** ({r['partner']}; ended: {r['outcome']})"
        turns = [f"> **{t['author']}**: {t['text']}" for t in sel]
        why = f"Why: {r['why_it_worked_or_failed']}"
        blocks.append("\n".join([head, "", *turns, "", why]))
    return "\n\n".join(blocks) if blocks else "(none selected; see reference.md)"


def core_rules(lines: list[str]) -> str:
    if not lines:
        return "(none; the sections below carry the rules)"
    return "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


def sources_list(manifest: dict) -> str:
    return "\n".join(f"- `{s['kind']}`: {s['path']}: {s['note']}" for s in manifest["sources"])


def build_values(manifest: dict, records: list[dict], spec: dict, plugin_version: str) -> dict[str, str]:
    training, held_out = split_records(manifest, records)
    s = spec["sections"]
    ident = spec["identity"]
    return {
        "skill_name": ident["skill_name"],
        "one_line": ident["one_line"],
        "trigger_description": ident["trigger_description"],
        "dataset_name": manifest["name"],
        "dataset_version": manifest["version"],
        "pattern": manifest["pattern"],
        "sources": sources_list(manifest),
        "record_count": str(len(records)),
        "training_count": str(len(training)),
        "held_out_count": str(len(held_out)),
        "held_out_ids": ", ".join(sorted(manifest["held_out_ids"])) or "(none)",
        "plugin_version": plugin_version,
        "language": bullets(s["Language"]),
        "behaviour": bullets(s["Behaviour"]),
        "communication_style": bullets(s["Communication style"]),
        "demeanor": bullets(s["Demeanor"]),
        "motivations": bullets(s["Motivations"]),
        "moves_opening": bullets(s["Moves: opening"]),
        "moves_escalation": bullets(s["Moves: escalation"]),
        "moves_repair": bullets(s["Moves: repair"]),
        "moves_exit": bullets(s["Moves: exit"]),
        "moves_table": moves_table(training),
        "phrase_bank": phrase_bullets(spec["phrases"]),
        "anti_patterns": anti_pattern_bullets(spec["anti_patterns"]),
        "self_lines": self_lines(training),
        "why_it_helps": ident["why_it_helps"],
        "benefits": bullets(s["Benefits"]),
        "when_not_to_use": ident["when_not_to_use"],
        "agent_protocol": bullets(s["Agent protocol"]) if s["Agent protocol"] else "(no agent protocol in the spec; this kind needs one)",
        "core_rules": core_rules(spec["core_rules"]),
        "inline_exemplars": inline_exemplars(training, spec["inline_exemplars"]),
        "exemplars": exemplars(training),
    }


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def render_canonical(out_dir: Path, values: dict[str, str], training: list[dict]) -> list[Path]:
    written = []
    for name in ("SKILL.md", "reference.md", "EVOLUTION.md", "PROTOCOL.md"):
        tpl = (TEMPLATES / name).read_text(encoding="utf-8")
        target = out_dir / name
        write(target, render(tpl, values, f"templates/{name}"))
        written.append(target)
    bank = out_dir / "dataset" / "bank.jsonl"
    import json

    lines = [json.dumps(r, sort_keys=True, ensure_ascii=False) for r in training]
    write(bank, "\n".join(lines) + "\n")
    written.append(bank)
    return written


def render_provider(target: str, out_dir: Path, values: dict[str, str]) -> list[Path]:
    src_dir = TEMPLATES / "providers" / target
    if not src_dir.is_dir():
        raise ContractError(f"no provider templates for target '{target}' at {src_dir}")
    written = []
    for tpl_path in sorted(p for p in src_dir.rglob("*") if p.is_file()):
        rel = tpl_path.relative_to(src_dir)
        rel_rendered = Path(render(str(rel), values, f"templates/providers/{target}/{rel} (filename)"))
        content = render(tpl_path.read_text(encoding="utf-8"), values, f"templates/providers/{target}/{rel}")
        target_path = out_dir / rel_rendered
        write(target_path, content)
        written.append(target_path)
    return written


def load_manifest() -> dict:
    build = read_json(BUILD_JSON)
    if build.get("version") != 1:
        raise ContractError("build.json: version must be 1")
    entries = build.get("builds")
    if not isinstance(entries, list) or not entries:
        raise ContractError("build.json: builds[] is empty")
    names = set()
    for e in entries:
        for key in ("dataset", "kind", "skill", "targets"):
            if key not in e:
                raise ContractError(f"build.json: entry missing '{key}': {e}")
        if e["kind"] not in KINDS:
            raise ContractError(
                f"build.json: kind '{e['kind']}' is not rendered by build.py in this version; "
                f"supported: {sorted(KINDS)}. Rules, hooks and DESIGN.md are rendered "
                f"by their forge-* skill."
            )
        if e["kind"] == "subagent" and e["targets"] != [CANONICAL_TARGET]:
            raise ContractError(f"build.json: kind 'subagent' renders for target '{CANONICAL_TARGET}' only ({e['skill']})")
        if not KEBAB.match(e["skill"]):
            raise ContractError(f"build.json: skill '{e['skill']}' must be kebab-case")
        if e["skill"] in names:
            raise ContractError(f"build.json: duplicate skill '{e['skill']}'")
        names.add(e["skill"])
        bad = [t for t in e["targets"] if t not in ALL_TARGETS]
        if bad:
            raise ContractError(f"build.json: unknown targets {bad}; known: {list(ALL_TARGETS)}")
        if CANONICAL_TARGET not in e["targets"]:
            raise ContractError(f"build.json: entry '{e['skill']}' must include target '{CANONICAL_TARGET}'")
        if not (DATASETS / e["dataset"]).is_dir():
            raise ContractError(f"build.json: dataset '{e['dataset']}' not found under datasets/")
    return build


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="render only this generated skill name")
    ap.add_argument("--check", action="store_true", help="validate inputs and render nothing")
    args = ap.parse_args(argv)

    try:
        plugin_version = read_json(PLUGIN_JSON)["version"]
        build = load_manifest()
        from common import parse_spec

        total = 0
        for entry in build["builds"]:
            if args.only and entry["skill"] != args.only:
                continue
            ds_dir = DATASETS / entry["dataset"]
            manifest, records = validate_dataset(ds_dir)
            spec = parse_spec(ds_dir / "spec.md")
            same = spec["identity"]["skill_name"] == entry["skill"]
            derived = entry["kind"] == "subagent" and entry["skill"].startswith(spec["identity"]["skill_name"] + "-")
            if not (same or derived):
                raise ContractError(
                    f"build.json skill '{entry['skill']}' != spec.md skill_name "
                    f"'{spec['identity']['skill_name']}' in {ds_dir}"
                )
            values = build_values(manifest, records, spec, plugin_version)
            training, _ = split_records(manifest, records)
            print(f"[build] {entry['skill']} <- {manifest['name']}@{manifest['version']} "
                  f"({len(training)} training, {len(records) - len(training)} held out)")
            if args.check:
                for t in entry["targets"]:
                    if t != CANONICAL_TARGET:
                        render_provider_check(t, values)
                continue
            for t in entry["targets"]:
                out_dir = GENERATED / t / entry["skill"]
                if out_dir.exists():
                    shutil.rmtree(out_dir)
                if entry["kind"] == "subagent":
                    if not spec["agent_protocol"]:
                        raise ContractError(f"{ds_dir}/spec.md: kind 'subagent' needs a non-empty '## Agent protocol'")
                    values = dict(values, skill_name=entry["skill"])
                    tpl = (TEMPLATES / "subagent.md").read_text(encoding="utf-8")
                    target = out_dir / "agents" / f"{entry['skill']}.md"
                    write(target, render(tpl, values, "templates/subagent.md"))
                    print(f"  wrote {target}")
                    total += 1
                    continue
                written = render_canonical(out_dir, values, training)
                if t != CANONICAL_TARGET:
                    written += render_provider(t, out_dir, values)
                for p in written:
                    print(f"  wrote {p}")
                total += len(written)
        if args.only and total == 0 and not args.check:
            raise ContractError(f"--only {args.only}: no such entry in build.json")
        print("[build] check ok" if args.check else f"[build] ok: {total} files")
        return 0
    except ContractError as exc:
        print(f"[build] error: {exc}", file=sys.stderr)
        return 1


def render_provider_check(target: str, values: dict[str, str]) -> None:
    src_dir = TEMPLATES / "providers" / target
    for tpl_path in sorted(p for p in src_dir.rglob("*") if p.is_file()):
        rel = tpl_path.relative_to(src_dir)
        render(str(rel), values, f"templates/providers/{target}/{rel} (filename)")
        render(tpl_path.read_text(encoding="utf-8"), values, f"templates/providers/{target}/{rel}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
