#!/usr/bin/env python3
"""Measure how many turns a session burns before a stated constraint sticks.

Turn-level signals say a user is annoyed. They do not say how much time the
miss cost. This miner walks each session in user-turn order, records the turn
a constraint is first stated, and records every later turn that restates it.
The intervening user turns are the wasted span: the agent had the constraint
and worked without it.

Writes counts and closed-vocabulary labels only. Never writes corpus message
text. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hooks.session_signals import detect  # noqa: E402

# Agent hosts only. Chat platforms (discord, reddit, skype) are not sessions
# where an agent could have carried a constraint forward.
DEFAULT_PLATFORMS = (
    "cursor",
    "claude_code",
    "codex",
    "copilot",
    "chatgpt",
    "agent",
    "commandcode",
    "continue",
    "openclaw",
)
AI_TYPES = {"assistant.session", "assistant.prompt_history"}
USER_ROLES = {"user", "self"}

# --- closed constraint vocabulary -------------------------------------------
# Each entry is (label, regex). The label is the emitted key, so nothing from
# the corpus reaches the output. Labels are coarse on purpose: two turns that
# both pin the distro collide on "env:fedora" and count as a restatement.
#
# Topics are gated. "the fedora build is broken" names a topic; "only fedora"
# states a constraint. A topic only becomes a constraint when a directive word
# sits within DIRECTIVE_WINDOW characters ahead of it. Directive specs already
# carry their own framing, so they skip the gate.

DIRECTIVE_WINDOW = 24
# Agent turns carry pasted logs and diffs. Constraints are stated in the ask,
# not 200KB down a stack trace, so bound the scan instead of reading the paste.
MAX_SCAN_CHARS = 8000
_DIRECTIVE_LEAD = re.compile(
    r"\b(?:only|just|exclusively|always|never|must|need(?:s)? to|use|using|"
    r"on|under|target(?:ing)?|stick to|keep it|it'?s|i'?m on|we'?re on|"
    r"don'?t|do not|no|not)\s+(?:\w+\s+){0,2}$",
    re.I,
)

_TOPIC_SPECS: tuple[tuple[str, str], ...] = (
    ("env:fedora", r"\bfedora\b"),
    ("env:kde", r"\bkde\b|\bplasma\b"),
    ("env:gnome", r"\bgnome\b"),
    ("env:ubuntu", r"\bubuntu\b"),
    ("env:debian", r"\bdebian\b"),
    ("env:arch", r"\barch\s*linux\b|\bpacman\b"),
    ("env:windows", r"\bwindows\b|\bwin(?:10|11)\b|\bpowershell\b"),
    ("env:macos", r"\bmac\s*os\b|\bmacos\b|\bosx\b"),
    ("env:wsl", r"\bwsl2?\b"),
    ("env:android", r"\bandroid\b"),
    ("runtime:python", r"\bpython\s*3?(?:\.\d+)?\b|\bvenv\b"),
    ("runtime:node", r"\bnode(?:js)?\b|\bnpm\b|\bpnpm\b|\byarn\b"),
    ("runtime:bun", r"\bbun\b|\bdeno\b"),
    ("runtime:rust", r"\brust\b|\bcargo\b"),
    ("runtime:java", r"\bjava\b|\bgradle\b|\bmaven\b"),
    ("runtime:dotnet", r"\bdotnet\b|\b\.net\b|\bc#\b"),
    ("tool:docker", r"\bdocker\b|\bpodman\b"),
    ("tool:systemd", r"\bsystemd\b|\bsystemctl\b"),
    ("tool:pkg", r"\bflatpak\b|\bdnf\b|\brpm\b|\bapt\b"),
)

_DIRECTIVE_SPECS: tuple[tuple[str, str], ...] = (
    ("git:no-commit", r"\b(?:don'?t|do not|never|stop|no)\s+(?:\w+\s+){0,2}commit"),
    ("git:no-push", r"\b(?:don'?t|do not|never|stop|no)\s+(?:\w+\s+){0,2}push"),
    ("git:no-github", r"\bno\s+github\b|\b(?:don'?t|do not)\s+(?:\w+\s+){0,2}github\b"),
    ("scope:no-rewrite", r"\b(?:don'?t|do not|stop)\s+(?:\w+\s+){0,2}rewrit"),
    ("scope:dont-touch", r"\b(?:don'?t|do not)\s+(?:\w+\s+){0,2}touch\b"),
    ("scope:one-file", r"\bonly\s+(?:the\s+)?(?:one|this|that)\s+file\b|\bjust\s+(?:the\s+)?one\s+file\b"),
    ("scope:leave-rest", r"\bleave\s+the\s+rest\b|\bnothing\s+else\b|\bdon'?t\s+add\s+anything\b"),
    ("ask:stop-asking", r"\bstop\s+asking\b|\bno\s+more\s+questions\b|\b(?:don'?t|do not)\s+ask\s+(?:me\s+)?again\b"),
    ("ask:stop-explaining", r"\b(?:stop|quit)\s+explain|\b(?:don'?t|do not)\s+explain\b"),
    ("fmt:less-writing", r"\bless\s+writing\b|\bbe\s+brief\b|\btoo\s+(?:long|verbose|wordy)\b|\bshorter\b"),
    ("fmt:plain", r"\bplain\s+english\b|\bin\s+plain\b|\bno\s+jargon\b"),
    ("fmt:no-comments", r"\bno\s+comments\b|\b(?:don'?t|do not)\s+(?:\w+\s+){0,2}comment"),
    ("fmt:answer-first", r"\banswer\s+first\b|\bjust\s+(?:the\s+)?answer\b|\bget\s+to\s+the\s+point\b"),
    ("act:no-placeholder", r"\bno\s+(?:placeholder|stub|todo|mock)s?\b|\b(?:don'?t|do not)\s+stub\b|\bnot?\s+placeholder\b"),
    ("act:finish-all", r"\ball\s+of\s+(?:them|it)\b|\bevery\s+(?:one|single)\b|\bthe\s+whole\s+thing\b|\bfully\s+implement\b"),
    ("act:actually-run", r"\bactually\s+(?:run|test|try|check)\b|\brun\s+it\s+(?:first|yourself)\b|\btest\s+it\s+first\b"),
    ("act:read-context", r"\bread\s+(?:the\s+)?(?:file|code|docs?|readme|agents\.md|claude\.md)\b|\blook\s+at\s+the\s+(?:file|code|actual)\b"),
)

TOPICS = tuple((label, re.compile(rx, re.I)) for label, rx in _TOPIC_SPECS)
DIRECTIVES = tuple((label, re.compile(rx, re.I)) for label, rx in _DIRECTIVE_SPECS)

# A restatement only counts when the turn also reads as a miss: the user is
# repeating themselves, correcting, or annoyed. A constraint mentioned twice in
# calm consecutive turns is normal conversation, not a wasted span.
_MISS_MARKERS = ("repeat_ask", "frustration", "correction", "scope_pushback", "do_it_already")


def _content(msg: dict) -> str:
    raw = msg.get("content")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return " ".join(parts)
    return ""


def _role(msg: dict) -> str:
    role = (msg.get("role") or "").lower()
    if role:
        return role
    author = msg.get("author")
    if isinstance(author, dict):
        return (author.get("role") or "").lower()
    return ""


def _labels(text: str) -> set[str]:
    """Constraint labels in this turn. Topics need a directive lead-in."""
    if len(text) > MAX_SCAN_CHARS:
        text = text[:MAX_SCAN_CHARS]
    found: set[str] = set()
    for label, rx in DIRECTIVES:
        if rx.search(text):
            found.add(label)
    for label, rx in TOPICS:
        for m in rx.finditer(text):
            lead = text[max(0, m.start() - DIRECTIVE_WINDOW):m.start()]
            if _DIRECTIVE_LEAD.search(lead):
                found.add(label)
                break
    return found


def mine_session(messages: list[dict]) -> dict:
    """Return per-session counts. No text leaves this function.

    Waste is charged once per restating turn, not once per label on it. A turn
    that re-pins the distro and re-forbids commits in the same breath is one
    missed turn, not two, so wasted turns can never exceed user turns.
    """
    first_seen: dict[str, int] = {}
    turn_events: list[dict] = []
    wasted_idx: set[int] = set()
    signal_turns: Counter[str] = Counter()
    user_turns = 0

    for msg in messages:
        if _role(msg) not in USER_ROLES:
            continue
        text = _content(msg)
        if not text.strip():
            continue
        user_turns += 1
        idx = user_turns

        signals = detect(text, session_context="prior turns exist" if idx > 1 else "")
        for sig in signals:
            signal_turns[sig] += 1
        is_miss = any(s in signals for s in _MISS_MARKERS)

        labels = _labels(text)
        restated: list[tuple[str, int]] = []
        for label in sorted(labels):
            if label not in first_seen:
                first_seen[label] = idx
                continue
            if is_miss:
                restated.append((label, idx - first_seen[label]))
                # Re-anchor so a third restatement measures from the second.
                first_seen[label] = idx

        if restated:
            # The span is set by the constraint that has been ignored longest.
            gap = max(g for _, g in restated)
            turn_events.append(
                {"turn": idx, "gap": gap, "labels": [lb for lb, _ in restated]}
            )
            # Turns the agent worked without a constraint it had already been
            # given. Spans from different constraints overlap, so union them:
            # a turn that ignored two constraints is still one wasted turn.
            wasted_idx.update(range(idx - gap + 1, idx + 1))

    return {
        "user_turns": user_turns,
        "turn_events": turn_events,
        "wasted_turns": len(wasted_idx),
        "signal_turns": dict(signal_turns),
        "constraints_stated": len(first_seen),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="corpus records/kind=conversation dir")
    ap.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0, help="max sessions per platform")
    args = ap.parse_args()

    root = Path(args.root)
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]

    totals = {
        "sessions": 0,
        "sessions_with_waste": 0,
        "user_turns": 0,
        "wasted_turns": 0,
        "recurrence_events": 0,
    }
    by_label_waste: Counter[str] = Counter()  # float shares
    by_label_events: Counter[str] = Counter()
    by_platform: dict[str, dict] = defaultdict(
        lambda: {"sessions": 0, "wasted_turns": 0, "events": 0, "user_turns": 0}
    )
    signal_totals: Counter[str] = Counter()
    gap_hist: Counter[str] = Counter()

    for plat in platforms:
        pdir = root / f"platform={plat}"
        if not pdir.is_dir():
            continue
        seen = 0
        for part in sorted(pdir.glob("*.jsonl")):
            with part.open("r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    if rec.get("type") not in AI_TYPES:
                        continue
                    msgs = rec.get("messages") or []
                    if not isinstance(msgs, list) or len(msgs) < 4:
                        continue
                    res = mine_session(msgs)
                    if res["user_turns"] < 2:
                        continue
                    seen += 1
                    totals["sessions"] += 1
                    totals["user_turns"] += res["user_turns"]
                    by_platform[plat]["sessions"] += 1
                    by_platform[plat]["user_turns"] += res["user_turns"]
                    for sig, n in res["signal_turns"].items():
                        signal_totals[sig] += n
                    if res["turn_events"]:
                        totals["sessions_with_waste"] += 1
                    totals["wasted_turns"] += res["wasted_turns"]
                    by_platform[plat]["wasted_turns"] += res["wasted_turns"]
                    for ev in res["turn_events"]:
                        gap = ev["gap"]
                        totals["recurrence_events"] += 1
                        by_platform[plat]["events"] += 1
                        bucket = (
                            "1" if gap == 1
                            else "2-3" if gap <= 3
                            else "4-7" if gap <= 7
                            else "8-15" if gap <= 15
                            else "16+"
                        )
                        gap_hist[bucket] += 1
                        # Attribution splits the span across the labels on the
                        # turn so per-label waste still sums to the total.
                        share = gap / len(ev["labels"])
                        for label in ev["labels"]:
                            by_label_waste[label] += share
                            by_label_events[label] += 1
                    if args.limit and seen >= args.limit:
                        break
            if args.limit and seen >= args.limit:
                break

    ranked = [
        {
            "label": label,
            "wasted_turns": round(by_label_waste[label], 1),
            "events": by_label_events[label],
            "mean_gap": round(by_label_waste[label] / by_label_events[label], 2),
            "share_of_attributed": round(by_label_waste[label] / sum(by_label_waste.values()), 3) if by_label_waste else 0.0,
        }
        for label in sorted(by_label_waste, key=lambda k: -by_label_waste[k])
    ]
    report = {
        "totals": totals,
        "waste_rate": round(
            totals["sessions_with_waste"] / totals["sessions"], 4
        ) if totals["sessions"] else 0.0,
        "wasted_turn_share": round(
            totals["wasted_turns"] / totals["user_turns"], 4
        ) if totals["user_turns"] else 0.0,
        "gap_histogram": dict(gap_hist),
        "ranked_by_wasted_turns": ranked,
        "turn_signal_totals": dict(signal_totals),
        "by_platform": {k: dict(v) for k, v in by_platform.items()},
        "text_written": False,
    }
    out = json.dumps(report, indent=2) + "\n"
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        print(dest)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
