#!/usr/bin/env python3
"""Score a generated skill against its dataset's spec and held-out records.

Usage:
    python3 scripts/evaluate.py --skill-dir generated/claude/<skill> --dataset datasets/<name>
    python3 scripts/evaluate.py ... --responses runs.jsonl --out scorecard.json

Computes the deterministic parts of the fidelity scorecard:
  phrase_bank    which spec phrases appear verbatim in the generated skill files
  anti_patterns  which spec anti-patterns the generated skill lists
  held_out       whether any held-out `self` line leaked into the generated files
  citations      every cited record id (r-NNN) exists and is not held out
  responses      (optional) phrase hits and anti-pattern marker hits per candidate response

The LLM-judged parts (pairwise old-vs-new, motivation score) are filled by the
fidelity-judge agent. This script leaves them null. Standard library only.
Output has sorted keys and no timestamps.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SUBJECT,
    ContractError,
    dump_json,
    parse_spec,
    read_records,
    split_records,
    validate_dataset,
)

PHRASE_PASS = 0.8
ANTI_PASS = 1.0


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def skill_text(skill_dir: Path) -> str:
    """Text under test: SKILL.md + reference.md in a directory, or one file (rule, agent, DESIGN.evidence.md)."""
    if skill_dir.is_file():
        return skill_dir.read_text(encoding="utf-8")
    if not (skill_dir / "SKILL.md").is_file():
        raise ContractError(f"{skill_dir}: no SKILL.md")
    parts = []
    for name in ("SKILL.md", "reference.md"):
        p = skill_dir / name
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def score_phrases(spec: dict, text: str) -> dict:
    hay = norm(text)
    found, missing = [], []
    for p in spec["phrases"]:
        (found if norm(p["phrase"]) in hay else missing).append(p["phrase"])
    total = len(spec["phrases"])
    return {
        "coverage": round(len(found) / total, 4) if total else 0.0,
        "found": sorted(found),
        "missing": sorted(missing),
        "total": total,
    }


def score_anti_patterns(spec: dict, text: str) -> dict:
    hay = norm(text)
    listed, missing = [], []
    for a in spec["anti_patterns"]:
        (listed if norm(a["description"]) in hay else missing).append(a["description"])
    total = len(spec["anti_patterns"])
    return {
        "coverage": round(len(listed) / total, 4) if total else 0.0,
        "listed": sorted(listed),
        "missing": sorted(missing),
        "total": total,
    }


LEAK_MIN_WORDS = 5  # "no", "fair", "lol" recur in any chat corpus; they are not leaks


def score_held_out(held_out: list[dict], text: str) -> dict:
    """A held-out `self` line has leaked when a distinctive line (LEAK_MIN_WORDS
    words or more) appears verbatim in the generated files. Real chat repeats
    short lines constantly, so those never count."""
    hay = norm(text)
    leaked = []
    for r in held_out:
        for t in r["turns"]:
            if t["author"] != SUBJECT:
                continue
            line = norm(t["text"])
            if len(line.split()) < LEAK_MIN_WORDS:
                continue
            if line in hay:
                leaked.append({"id": r["id"], "text": t["text"]})
    return {"ids": sorted(r["id"] for r in held_out), "leaked": leaked}


def score_citations(records: list[dict], held_out: list[dict], text: str) -> dict:
    """Every record id cited in the text must exist and must not be held out."""
    import re

    known = {r["id"] for r in records}
    held = {r["id"] for r in held_out}
    cited = sorted(set(re.findall(r"\br-\d{3,}\b", text)))
    return {
        "cited": cited,
        "held_out_cited": sorted(c for c in cited if c in held),
        "unknown": sorted(c for c in cited if c not in known),
    }


def score_responses(spec: dict, path: Path) -> list[dict]:
    rows = read_records(path)
    out = []
    for row in rows:
        for key in ("id", "text"):
            if key not in row:
                raise ContractError(f"{path}: response missing '{key}'")
        hay = norm(row["text"])
        phrase_hits = sorted(p["phrase"] for p in spec["phrases"] if norm(p["phrase"]) in hay)
        marker_hits = sorted(
            m for a in spec["anti_patterns"] for m in a["markers"] if norm(m) in hay
        )
        out.append(
            {
                "anti_pattern_marker_hits": marker_hits,
                "id": row["id"],
                "phrase_hits": phrase_hits,
                "prompt_record_id": row.get("prompt_record_id"),
            }
        )
    return sorted(out, key=lambda r: r["id"])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill-dir", required=True, type=Path,
                    help="generated skill directory, or a single file (rule, agent, DESIGN.evidence.md)")
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--responses", type=Path, help="JSONL of {id, prompt_record_id, text} candidate responses")
    ap.add_argument("--out", type=Path, help="write scorecard JSON here instead of stdout")
    args = ap.parse_args(argv)

    try:
        manifest, records = validate_dataset(args.dataset)
        spec = parse_spec(args.dataset / "spec.md")
        _, held_out = split_records(manifest, records)
        text = skill_text(args.skill_dir)

        phrases = score_phrases(spec, text)
        antis = score_anti_patterns(spec, text)
        held = score_held_out(held_out, text)
        cites = score_citations(records, held_out, text)
        checks = {
            "anti_patterns_listed": antis["coverage"] >= ANTI_PASS,
            "citations_resolve": not cites["unknown"] and not cites["held_out_cited"],
            "no_held_out_leak": not held["leaked"],
            "phrase_bank_coverage": phrases["coverage"] >= PHRASE_PASS,
        }
        card = {
            "anti_patterns": antis,
            "checks": checks,
            "citations": cites,
            "dataset": {"name": manifest["name"], "version": manifest["version"]},
            "held_out": held,
            "llm_judged": {
                "motivation_score": None,
                "note": "Run the fidelity-judge agent via /evaluate-fidelity to fill these.",
                "pairwise": None,
            },
            "phrase_bank": phrases,
            "skill": spec["identity"]["skill_name"],
            "skill_dir": str(args.skill_dir),
            "thresholds": {"anti_patterns": ANTI_PASS, "phrase_bank": PHRASE_PASS},
            "verdict": "pass" if all(checks.values()) else "fail",
        }
        if args.responses:
            card["responses"] = score_responses(spec, args.responses)
        out = dump_json(card)
        if args.out:
            args.out.write_text(out, encoding="utf-8")
            print(f"[evaluate] {card['verdict']}: wrote {args.out}")
        else:
            sys.stdout.write(out)
        return 0 if card["verdict"] == "pass" else 2
    except ContractError as exc:
        print(f"[evaluate] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
