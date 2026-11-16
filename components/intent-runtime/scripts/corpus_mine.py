#!/usr/bin/env python3
"""Extract and classify self-authored assistant-platform prompts.

Reads UPAR v1 conversation JSONL from a personal archive, keeps only
messages whose author.role is "self", buckets them into prompt families,
and writes a sanitized analysis plus activation-eval seeds.

Does not write raw corpus text into the repo unless --write-eval is set,
and then only after sanitization.

Usage:
    python3 scripts/corpus_mine.py \\
        --root /path/to/authorized/archive \\
        --analysis docs/research/prompt-pattern-analysis.md \\
        --eval evals/activation/cases.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hooks.prescreen import looks_already_complete  # noqa: E402

ASSISTANT_PLATFORMS = {
    "chatgpt",
    "claude_code",
    "codex",
    "commandcode",
    "continue",
    "copilot",
    "cursor",
    "deepseek",
    "gemini",
    "grok",
    "lmstudio",
    "openclaw",
    "perplexity",
    "agent",
}

# Observable feature regexes. These are cheap signals, not the family labels.
RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
RE_URL = re.compile(r"https?://\S+")
RE_HOME = re.compile(r"/(?:home|Users|run/media)/[A-Za-z0-9._-]+")
RE_KEYISH = re.compile(
    r"\b(?:sk-|ghp_|xox[baprs]-|AKIA)[A-Za-z0-9_-]{8,}\b"
)
RE_LONG_HEX = re.compile(r"\b[0-9a-f]{24,}\b", re.I)
RE_PROFANITY = re.compile(
    r"\b(?:fuck|fucking|shit|bullshit|ass|damn|wtf|tf|hell)\b", re.I
)
RE_SLANG = re.compile(
    r"\b(?:bro|lol|lmao|idk|imo|imho|nah|yeah|yep|gonna|wanna|kinda|"
    r"tho|thx|pls|plz|rn|af|lowkey|highkey|ngl|fr|bruh)\b",
    re.I,
)
RE_DEIXIS = re.compile(
    r"\b(?:this|that|it|these|those|the thing|the one|same)\b", re.I
)
RE_FRAGMENT_START = re.compile(
    r"^(?:yeah|yep|ok|okay|and|but|also|then|now|just|only|same)\b", re.I
)
RE_CORRECTION = re.compile(
    r"\b(?:no[, ]|wait[, ]|actually|i meant|not that|instead|"
    r"don't|dont|stop|undo|revert)\b",
    re.I,
)
RE_QUESTION = re.compile(r"\?")
RE_DEBUG = re.compile(
    r"\b(?:why|broken|fail(?:s|ed|ing)?|error|bug|crash|sort(?:ing)?|"
    r"doesn't work|doesnt work|not working)\b",
    re.I,
)
RE_LOOKUP = re.compile(
    r"\b(?:look(?:ing)? (?:this )?up|look into|research|find me|"
    r"what's|whats|how do i|how to|search)\b",
    re.I,
)
RE_DISSATISFACTION = re.compile(
    r"\b(?:sucks|hate|awful|terrible|worse|better|replace|instead of)\b",
    re.I,
)
RE_PRESENTATION = re.compile(
    r"\b(?:concise|brief|less writing|plain english|eli\d+|dm style|"
    r"don't sound|dont sound|bullets|table|short|no intro|second person)\b",
    re.I,
)
RE_META = re.compile(
    r"\b(?:your prompt|system prompt|you are an? |as an ai|"
    r"ignore previous|jailbreak)\b",
    re.I,
)
RE_ACK = re.compile(
    r"^(?:thanks|thank you|ok|okay|cool|nice|got it|lgtm|sounds good|"
    r"perfect|great)\b[.!]*$",
    re.I,
)
RE_MISSION_CMD = re.compile(
    r"^/(?:mission|mission-brief|mission-resume|mission-status|"
    r"mission-telemetry)\b",
    re.I,
)

FAMILIES = (
    "debug_frustration",
    "continuation_fragment",
    "vague_lookup",
    "recommendation_dissatisfaction",
    "deixis_unresolved",
    "correction_after",
    "mixed_task_and_style",
    "disorganized_detailed",
    "already_excellent",
    "meta_discussion",
    "acknowledgment",
    "mission_command",
    "other_task",
)


def sanitize(text: str) -> str:
    text = RE_EMAIL.sub("<email>", text)
    text = RE_KEYISH.sub("<secret>", text)
    text = RE_URL.sub("<url>", text)
    text = RE_HOME.sub("<home>", text)
    text = RE_LONG_HEX.sub("<id>", text)
    for name in json.loads(os.environ.get("INTENT_RUNTIME_REDACT_NAMES", "[]")):
        if isinstance(name, str) and name.strip():
            text = re.sub(r"\b" + re.escape(name) + r"\b", "<name>", text, flags=re.IGNORECASE)
    return text.strip()


def message_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in (None, "text") and "text" in block:
                    parts.append(str(block["text"]))
        return "\n".join(parts)
    return ""


def is_self(msg: dict) -> bool:
    author = msg.get("author") or {}
    if author.get("role") == "self":
        return True
    # ChatML fallback: user turns that are not tool/system.
    if msg.get("role") == "user" and author.get("role") not in {
        "assistant",
        "tool",
        "meta",
        "system",
    }:
        # Only count as self when the archive marked it, or when there is
        # no author block at all on a user turn (some older exports).
        return author.get("role") == "self"
    return False


def classify(text: str, is_first: bool) -> str:
    stripped = text.strip()
    words = stripped.split()
    n = len(words)
    if RE_MISSION_CMD.search(stripped):
        return "mission_command"
    if n <= 8 and RE_ACK.match(stripped):
        return "acknowledgment"
    if RE_META.search(stripped) and n < 40:
        return "meta_discussion"
    if RE_PROFANITY.search(stripped) and RE_DEBUG.search(stripped):
        return "debug_frustration"
    if RE_DISSATISFACTION.search(stripped) and (
        RE_LOOKUP.search(stripped) or "better" in stripped.lower()
    ):
        return "recommendation_dissatisfaction"
    if n <= 12 and RE_DEIXIS.search(stripped) and (
        RE_QUESTION.search(stripped) or re.search(r"\b(?:what'?s|whats|why|how)\b", stripped, re.I)
    ):
        return "deixis_unresolved"
    if (
        (not is_first)
        and n <= 18
        and (
            RE_FRAGMENT_START.search(stripped)
            or (RE_DEIXIS.search(stripped) and n <= 12)
        )
    ):
        return "continuation_fragment"
    if n <= 16 and RE_LOOKUP.search(stripped) and RE_DEIXIS.search(stripped):
        return "vague_lookup"
    if (not is_first) and RE_CORRECTION.search(stripped) and n <= 40:
        return "correction_after"
    if RE_PRESENTATION.search(stripped) and n >= 8:
        return "mixed_task_and_style"
    if n >= 80 and not _looks_excellent(stripped):
        return "disorganized_detailed"
    if n >= 30 and _looks_excellent(stripped):
        return "already_excellent"
    if n <= 6 and RE_DEBUG.search(stripped):
        return "debug_frustration"
    if n <= 10 and RE_LOOKUP.search(stripped):
        return "vague_lookup"
    return "other_task"


def _looks_excellent(text: str) -> bool:
    return looks_already_complete(text)


def extract_self_turns(record: dict, platform: str):
    messages = record.get("messages") or []
    self_index = 0
    prev_self = ""
    for msg in messages:
        if not is_self(msg):
            continue
        text = message_text(msg).strip()
        if not text:
            continue
        # Skip tool-result dumps and huge pasted files.
        if text.startswith("[tool_use:") or text.startswith("[tool_result"):
            continue
        if len(text) > 8000:
            text = text[:8000]
        is_first = self_index == 0
        family = classify(text, is_first)
        yield {
            "platform": platform,
            "family": family,
            "is_first": is_first,
            "n_words": len(text.split()),
            "n_chars": len(text),
            "has_profanity": bool(RE_PROFANITY.search(text)),
            "has_slang": bool(RE_SLANG.search(text)),
            "has_deixis": bool(RE_DEIXIS.search(text)),
            "has_typo_signal": bool(
                re.search(r"\b(?:teh|dont|wont|cant|whats|im )\b", text, re.I)
            ),
            "text": text,
            "prev_self": prev_self[:400] if prev_self else "",
        }
        prev_self = text
        self_index += 1


def iter_records(root: Path):
    conv = root / "archive" / "corpus" / "records" / "kind=conversation"
    if not conv.is_dir():
        raise SystemExit(f"no conversation records under {conv}")
    for plat_dir in sorted(conv.glob("platform=*")):
        platform = plat_dir.name.split("=", 1)[1]
        if platform not in ASSISTANT_PLATFORMS:
            continue
        for part in sorted(plat_dir.glob("*.jsonl")):
            with part.open(encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        print(
                            f"schema-skip {part}:{line_no}: {exc}",
                            file=sys.stderr,
                        )
                        continue
                    yield platform, rec


def pick_examples(bucket: list, n: int, rng: random.Random) -> list:
    if len(bucket) <= n:
        return list(bucket)
    # Prefer short, distinctive items for the analysis doc.
    ranked = sorted(bucket, key=lambda t: (t["n_words"], t["n_chars"]))
    head = ranked[: max(n * 3, n)]
    return rng.sample(head, n)


def expected_verdict(family: str) -> str:
    if family in {
        "acknowledgment",
        "meta_discussion",
        "already_excellent",
    }:
        return "should_not_trigger"
    if family == "other_task":
        return "ambiguous"
    return "should_trigger"


def write_analysis(path: Path, stats: dict, examples: dict, platforms: Counter):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Prompt-pattern analysis",
        "",
        "Derived from self-authored turns on assistant platforms in the",
        "UPAR v1 personal archive. Examples are sanitized. Raw corpus",
        "text is not stored in this repository.",
        "",
        f"Mined: {stats['n_records']} conversation records, "
        f"{stats['n_turns']} self-authored turns, "
        f"{stats['schema_errors']} schema errors.",
        "",
        "## Per-platform record counts",
        "",
        "| Platform | Records | Self turns |",
        "|---|---:|---:|",
    ]
    for plat, nrec in platforms.most_common():
        nturns = stats["turns_by_platform"].get(plat, 0)
        lines.append(f"| {plat} | {nrec} | {nturns} |")
    lines += [
        "",
        "## Feature rates (self turns)",
        "",
        f"- First-in-conversation: {stats['n_first']} "
        f"({_pct(stats['n_first'], stats['n_turns'])})",
        f"- Follow-up: {stats['n_follow']} "
        f"({_pct(stats['n_follow'], stats['n_turns'])})",
        f"- ≤12 words: {stats['n_short']} "
        f"({_pct(stats['n_short'], stats['n_turns'])})",
        f"- Profanity marker: {stats['n_profanity']} "
        f"({_pct(stats['n_profanity'], stats['n_turns'])})",
        f"- Slang marker: {stats['n_slang']} "
        f"({_pct(stats['n_slang'], stats['n_turns'])})",
        f"- Deixis (this/that/it): {stats['n_deixis']} "
        f"({_pct(stats['n_deixis'], stats['n_turns'])})",
        "",
        "## Semantic families",
        "",
        "Families are assigned by cheap observable signals, then used as",
        "the activation-eval strata. The skill must match the *behavior*,",
        "not these regexes.",
        "",
        "| Family | Turns | Activation seed |",
        "|---|---:|---|",
    ]
    for fam in FAMILIES:
        n = stats["by_family"].get(fam, 0)
        lines.append(f"| `{fam}` | {n} | {expected_verdict(fam)} |")
    lines += [
        "",
        "## Family notes and sanitized examples",
        "",
    ]
    notes = {
        "debug_frustration": (
            "Why-is-this-broken, often with profanity or settings named "
            "in passing. Activate; recover the setting/context; investigate."
        ),
        "continuation_fragment": (
            "Yeah-do-that / only-fedora / just-july. Meaning lives in "
            "the previous turn. Activate; resolve the referent; do not "
            "re-ask the original task."
        ),
        "vague_lookup": (
            "Look this up / what's this / find me X. Activate; resolve "
            "'this'; research with recovered criteria."
        ),
        "recommendation_dissatisfaction": (
            "This thing sucks, find something better. Convert complaints "
            "into criteria; do not demand a requirements doc."
        ),
        "deixis_unresolved": (
            "What's this mean / do the same for that one. The object is "
            "in the conversation or an attachment, not the sentence."
        ),
        "correction_after": (
            "No, wait, I meant Fedora. A later turn amends the task. "
            "The compiled spec must use the amendment, not the first ask."
        ),
        "mixed_task_and_style": (
            "Look into this repo thoroughly. Less writing, more snippets. "
            "Split: evidence requirement goes to the executor; brevity "
            "stays at the parent."
        ),
        "disorganized_detailed": (
            "Long, technically rich, poorly ordered. Activate with "
            "light reconstruction — reorder and fence, do not invent."
        ),
        "already_excellent": (
            "Names outcome, constraints, and a check. Minimal or no "
            "rewrite. Do not inflate."
        ),
        "meta_discussion": (
            "Talking about prompts or the assistant, not asking for work. "
            "Do not activate the runtime."
        ),
        "acknowledgment": (
            "Thanks / ok / lgtm. Conversational close. Do not activate."
        ),
        "mission_command": (
            "Slash plus English is a job. Bare /mission only is pass-through."
        ),
        "other_task": (
            "A real ask that did not match a more specific family. "
            "Often a short but complete instruction. Ambiguous for "
            "activation — treat as should-trigger only when context "
            "recovery or constraint split would change the outcome."
        ),
    }
    for fam in FAMILIES:
        lines.append(f"### `{fam}`")
        lines.append("")
        lines.append(notes[fam])
        lines.append("")
        shown = examples.get(fam, [])
        if not shown:
            lines.append("_No examples sampled._")
            lines.append("")
            continue
        for i, ex in enumerate(shown, 1):
            snippet = sanitize(ex["text"])
            if len(snippet) > 280:
                snippet = snippet[:277] + "..."
            snippet = snippet.replace("\n", " / ")
            pos = "first" if ex["is_first"] else "follow-up"
            lines.append(
                f"{i}. ({ex['platform']}, {pos}, {ex['n_words']} words) "
                f"`{snippet}`"
            )
        lines.append("")
    lines += [
        "## Activation implications",
        "",
        "The automatic skill's `description` / `when_to_use` should name",
        "the *behaviors* above — short fragments, deixis, frustration,",
        "mixed style+task, poorly ordered detail — and explicitly exclude",
        "acknowledgments, meta-discussion, and already-complete specs.",
        "Do not stuff hundreds of example phrases into the description;",
        "the listing cap is 1,536 combined characters.",
        "",
        "Mined by `scripts/corpus_mine.py`.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pct(part: int, whole: int) -> str:
    if not whole:
        return "0%"
    return f"{100.0 * part / whole:.1f}%"


def write_eval_seeds(path: Path, examples: dict, extras: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    cid = 1
    for fam in FAMILIES:
        verdict = expected_verdict(fam)
        for ex in examples.get(fam, []):
            prior = sanitize(ex["prev_self"]) if ex["prev_self"] else ""
            cases.append(
                {
                    "id": f"act-{cid:03d}",
                    "family": fam,
                    "class": _case_class(fam, ex),
                    "expected": verdict,
                    "prompt": sanitize(ex["text"])[:500],
                    "prior_turns": [prior] if prior and not ex["is_first"] else [],
                    "platform": ex["platform"],
                }
            )
            cid += 1
    for extra in extras:
        extra = dict(extra)
        extra["id"] = f"act-{cid:03d}"
        cases.append(extra)
        cid += 1
    with path.open("w", encoding="utf-8") as fh:
        for case in cases:
            fh.write(json.dumps(case, ensure_ascii=False) + "\n")
    return len(cases)


def _case_class(fam: str, ex: dict) -> str:
    if fam in {"acknowledgment", "meta_discussion"}:
        return "conversational"
    if fam == "already_excellent":
        return "already_excellent"
    if fam == "continuation_fragment":
        return "short_followup"
    if fam == "debug_frustration" and ex.get("has_profanity"):
        return "frustrated"
    if ex.get("has_slang"):
        return "slang"
    if ex.get("has_typo_signal"):
        return "typo_heavy"
    if fam == "disorganized_detailed":
        return "disorganized_detailed"
    if fam == "deixis_unresolved" or (
        ex.get("has_deixis") and not ex.get("is_first")
    ):
        return "context_dependent"
    if fam == "other_task":
        return "ambiguous"
    return "should_trigger" if expected_verdict(fam) == "should_trigger" else "should_not_trigger"


# Authored case data stays external to the portable source component.
HAND_CASES = []


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--analysis", type=Path)
    p.add_argument("--eval", dest="eval_path", type=Path)
    p.add_argument("--examples-per-family", type=int, default=6)
    p.add_argument("--seed", type=int, default=13)
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    platforms = Counter()
    by_family = defaultdict(list)
    stats = {
        "n_records": 0,
        "n_turns": 0,
        "schema_errors": 0,
        "n_first": 0,
        "n_follow": 0,
        "n_short": 0,
        "n_profanity": 0,
        "n_slang": 0,
        "n_deixis": 0,
        "by_family": Counter(),
        "turns_by_platform": Counter(),
    }

    for platform, rec in iter_records(args.root):
        stats["n_records"] += 1
        platforms[platform] += 1
        for turn in extract_self_turns(rec, platform):
            stats["n_turns"] += 1
            stats["turns_by_platform"][platform] += 1
            stats["by_family"][turn["family"]] += 1
            if turn["is_first"]:
                stats["n_first"] += 1
            else:
                stats["n_follow"] += 1
            if turn["n_words"] <= 12:
                stats["n_short"] += 1
            if turn["has_profanity"]:
                stats["n_profanity"] += 1
            if turn["has_slang"]:
                stats["n_slang"] += 1
            if turn["has_deixis"]:
                stats["n_deixis"] += 1
            bucket = by_family[turn["family"]]
            if len(bucket) < 400:
                bucket.append(turn)

    examples = {
        fam: pick_examples(by_family.get(fam, []), args.examples_per_family, rng)
        for fam in FAMILIES
    }

    print(
        json.dumps(
            {
                "records": stats["n_records"],
                "self_turns": stats["n_turns"],
                "schema_errors": stats["schema_errors"],
                "by_family": dict(stats["by_family"]),
                "platforms": dict(platforms),
            },
            indent=2,
        )
    )

    if args.analysis:
        write_analysis(args.analysis, stats, examples, platforms)
        print(f"wrote {args.analysis}", file=sys.stderr)
    if args.eval_path:
        n = write_eval_seeds(args.eval_path, examples, HAND_CASES)
        print(f"wrote {n} eval seeds to {args.eval_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
