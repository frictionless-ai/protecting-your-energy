#!/usr/bin/env python3
"""Score markdown/text for deslop tells and voice-match budgets.

Usage:
  python3 score.py path/to/file.md
  python3 score.py --register internal path/to/file.md
  python3 score.py --json README.md docs/essay.md

Registers: internal (default), public, portfolio
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# Generic editing diagnostics; these phrases are review leads.
ZERO_HIT_PHRASES = [
    "it's worth noting",
    "it is worth noting",
    "i hope this helps",
    "let's dive in",
    "in conclusion",
    "to summarize",
    "in summary",
    "delve into",
    "landscape of",
    "it's important to note",
    "at the end of the day",
    "game-changer",
    "cutting-edge",
    "seamless",
    "robust",
    "enterprise-grade",
    "holistic",
    "leverage",
    "utilize",
]

BUZZWORDS = [
    "seamless",
    "robust",
    "powerful",
    "intuitive",
    "cutting-edge",
    "next-gen",
    "enterprise-grade",
    "unified",
    "granular",
    "holistic",
    "leverage",
    "utilize",
]

CONCLUSION_MARKERS = [
    re.compile(r"^##?\s+if you remember one thing", re.I | re.M),
    re.compile(r"^##?\s+in (summary|conclusion)", re.I | re.M),
    re.compile(r"^TL;?DR", re.I | re.M),
]

TLDR_TOP = re.compile(r"^TL;?DR", re.I | re.M)

REFUSAL_FRONTMATTER = (
    "artifact_contract:",
    "machine-generated",
    "ce-unified-plan",
)


def strip_frontmatter(text: str) -> tuple[str, str | None]:
    if not text.startswith("---"):
        return text, None
    end = text.find("\n---", 3)
    if end == -1:
        return text, None
    return text[end + 4 :].lstrip("\n"), text[: end + 4]


def prose_only(text: str) -> str:
    """Drop fenced blocks and inline code for prose metrics."""
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"^\s*[-|].*$", " ", text, flags=re.M)
    return text


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", prose_only(text))
    return [s.strip() for s in chunks if len(s.strip()) > 10]


def em_dash_count(text: str) -> int:
    return text.count("—") + text.count(" -- ")


def first_person_count(text: str) -> int:
    return len(
        re.findall(
            r"\b(I|I'm|I've|I'd|I'll|my|mine|me|we|we're|we've|our)\b",
            prose_only(text),
            re.I,
        )
    )


def negative_definition_count(text: str) -> int:
    return len(re.findall(r"\bnot\b", prose_only(text), re.I))


def score_file(path: Path, register: str, profile: dict | None = None) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    body, fm = strip_frontmatter(raw)
    body_for_refusal = (fm or "") + body

    refusal_reasons = []
    if fm and any(k in fm for k in REFUSAL_FRONTMATTER):
        refusal_reasons.append("machine_contract_frontmatter")
    if "machine-generated" in body_for_refusal.lower():
        refusal_reasons.append("machine_generated_label")

    prose = prose_only(body)
    words = word_count(prose)
    sents = sentences(body)
    sent_lens = [word_count(s) for s in sents] if sents else [0]

    lower = prose.lower()
    zero_hits = {p: lower.count(p) for p in ZERO_HIT_PHRASES if lower.count(p)}
    buzz = {b: len(re.findall(rf"\b{re.escape(b)}\b", lower, re.I)) for b in BUZZWORDS}
    buzz = {k: v for k, v in buzz.items() if v}

    em_per_10k = (em_dash_count(body) / max(words, 1)) * 10000
    fp_per_1k = (first_person_count(body) / max(words, 1)) * 1000
    neg_per_10k = (negative_definition_count(body) / max(words, 1)) * 10000

    tldr_at_top = bool(TLDR_TOP.search(body[:400]))
    conclusion_section = any(p.search(body) for p in CONCLUSION_MARKERS)

    deslop_hits = sum(zero_hits.values()) + sum(buzz.values())
    deslop_verdict = "CLEAN" if deslop_hits == 0 else "PROCEED"

    budgets = (profile or {}).get("registers", {}).get(register, {})
    if not isinstance(budgets, dict):
        raise ValueError("profile register budgets must be an object")
    voice_flags = []
    for key, measured in (("max_em_dash_per_10k", em_per_10k),
                          ("max_first_person_per_1k", fp_per_1k),
                          ("max_median_sentence_words", statistics.median(sent_lens))):
        limit = budgets.get(key)
        if isinstance(limit, (int, float)) and not isinstance(limit, bool) and measured > limit:
            voice_flags.append(key + "_exceeded")
    if budgets.get("forbid_conclusion_section") and conclusion_section:
        voice_flags.append("conclusion_section_present")
    if budgets.get("forbid_top_tldr") and tldr_at_top:
        voice_flags.append("tldr_at_top")
    if budgets.get("require_no_deslop_hits") and deslop_hits:
        voice_flags.append("deslop_hits_present")
    configured_budgets = any(value is True or (isinstance(value, (int, float)) and not isinstance(value, bool)) for value in budgets.values())
    voice_verdict = ("MATCH" if not voice_flags else "GAP") if configured_budgets else "UNPROFILED"

    return {
        "path": str(path),
        "register": register,
        "refusal": refusal_reasons or None,
        "words": words,
        "sentences": len(sents),
        "median_sentence_words": round(statistics.median(sent_lens), 1),
        "em_dash_per_10k": round(em_per_10k, 2),
        "first_person_per_1k": round(fp_per_1k, 2),
        "negative_def_per_10k": round(neg_per_10k, 2),
        "zero_hit_phrases": zero_hits or None,
        "buzzwords": buzz or None,
        "conclusion_section": conclusion_section,
        "tldr_at_top": tldr_at_top,
        "deslop_score": deslop_hits,
        "deslop_verdict": deslop_verdict,
        "voice_flags": voice_flags or None,
        "voice_verdict": voice_verdict,
    }


def infer_register(path: Path) -> str:
    parts = path.as_posix()
    if "docs/essays" in parts or path.name == "AGENTS.md":
        return "internal"
    if "docs/plans" in parts:
        return "refuse"
    if path.name in ("README.md", "CHANGELOG.md"):
        return "public"
    return "internal"


def main() -> int:
    parser = argparse.ArgumentParser(description="Score prose for deslop and voice match")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--register", choices=("internal", "public", "portfolio"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--profile", type=Path, help="private JSON register budgets")
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text()) if args.profile else None
    if profile is not None and (not isinstance(profile, dict) or not isinstance(profile.get("registers", {}), dict)):
        parser.error("profile must contain a registers object")
    results = []
    for p in args.paths:
        reg = args.register or infer_register(p)
        if reg == "refuse":
            results.append({"path": str(p), "refusal": ["machine_contract_path"], "register": "refuse"})
            continue
        results.append(score_file(p.resolve(), reg, profile))

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if r.get("refusal"):
                print(f"{r['path']}\tREFUSE\t{','.join(r['refusal'])}")
                continue
            print(
                f"{r['path']}\t"
                f"deslop={r['deslop_verdict']}({r['deslop_score']})\t"
                f"voice={r['voice_verdict']}\t"
                f"words={r['words']}\t"
                f"med_sent={r['median_sentence_words']}\t"
                f"em/10k={r['em_dash_per_10k']}"
            )
            if r.get("zero_hit_phrases"):
                print(f"  zero_hits: {r['zero_hit_phrases']}")
            if r.get("buzzwords"):
                print(f"  buzz: {r['buzzwords']}")
            if r.get("voice_flags"):
                print(f"  voice_flags: {r['voice_flags']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
