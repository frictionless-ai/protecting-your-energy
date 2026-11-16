"""Carry constraints already stated in a session into the next contract.

Mined from the local agent archive by ``scripts/mine_intent_gaps.py``, which
measures *constraint recurrence distance*: the turn a constraint is first
stated, the later turn where the user restates it while annoyed, and the
turns in between. Those in-between turns are the cost. Ranked by wasted
turns, the classes that dominate are git prohibitions, single-file scope,
output format, and stop-asking.

``session_signals.lift_constraints`` only matches line-anchored context, so a
constraint stated mid-sentence never survives into the next contract. This
module reads anywhere in the context and returns the user's own phrase,
bounded, so nothing is invented on their behalf.

Operates on the caller's own session text only. Stdlib only.
"""

from __future__ import annotations

import re

MAX_PHRASE_CHARS = 72
MAX_CARRIED = 10

# Each spec is (class, regex). The class is documentation; the emitted value is
# always the user's own matched phrase, never a label we made up.
_CARRY_SPECS: tuple[tuple[str, str], ...] = (
    (
        "env",
        r"(?:only|just|use|using|on|under|target(?:ing)?|running|stick to|"
        r"i'?m on|we'?re on)\s+(?:\w+\s+){0,2}"
        r"(?:fedora|kde|plasma|gnome|ubuntu|debian|arch\s*linux|windows|"
        r"mac\s*os|macos|wsl2?|android|linux)\b[^.;\n]{0,32}",
    ),
    (
        "prohibition",
        r"(?:don'?t|do not|never|stop|no more)\s+(?:\w+\s+){0,2}"
        r"(?:commit|push|ask|rewrite|touch|explain|stub|mock|refactor|"
        r"delete|install|add)\b[^.;\n]{0,32}",
    ),
    (
        "scope",
        r"(?:only|just)\s+(?:the\s+)?(?:one|this|that|a\s+single)\s+"
        r"(?:file|function|line|change|thing|test)\b[^.;\n]{0,32}",
    ),
    (
        "scope",
        r"(?:leave\s+the\s+rest|nothing\s+else|don'?t\s+add\s+anything|"
        r"that'?s\s+all\s+i\s+asked)\b[^.;\n]{0,32}",
    ),
    (
        "format",
        r"(?:plain\s+english|no\s+jargon|be\s+brief|less\s+writing|"
        r"no\s+comments|answer\s+first|get\s+to\s+the\s+point|"
        r"stop\s+explaining)\b[^.;\n]{0,32}",
    ),
    (
        "completeness",
        r"(?:all\s+of\s+(?:them|it)|every\s+(?:one|single)|fully\s+implement|"
        r"the\s+whole\s+thing|no\s+placeholders?|no\s+stubs?|no\s+todos?)"
        r"\b[^.;\n]{0,32}",
    ),
    (
        "verification",
        r"(?:actually\s+(?:run|test|try|check)|test\s+it\s+first|"
        r"run\s+it\s+yourself|verify\s+it)\b[^.;\n]{0,32}",
    ),
)

_CARRY = tuple((cls, re.compile(rx, re.I)) for cls, rx in _CARRY_SPECS)

# How the answer should read is not a constraint on the work. The runtime keeps
# the two channels apart: task constraints render under Constraints,
# presentation renders under Output.
PRESENTATION_CLASSES = frozenset({"format"})


# The bounded tail can run past the constraint into the next clause. Trailing
# function words carry no constraint, so drop them rather than quote noise back.
_TAIL_STOPWORDS = frozenset(
    "and or but so on in to the a an with for at of by that which then also"
    " is are was were be please".split()
)


def _normalize(raw: str) -> str:
    phrase = " ".join(raw.split()).strip(" ,-–—")
    if len(phrase) > MAX_PHRASE_CHARS:
        phrase = phrase[:MAX_PHRASE_CHARS].rsplit(" ", 1)[0]
    words = phrase.split()
    while len(words) > 2 and words[-1].lower().strip(",") in _TAIL_STOPWORDS:
        words.pop()
    return " ".join(words).strip(" ,-–—")


def _collect(session_context: str, wanted: set[str] | None) -> list[str]:
    """Shared scan. ``wanted`` filters by class; None keeps every class."""

    ctx = session_context or ""
    if not ctx.strip():
        return []

    hits: list[tuple[int, str]] = []
    for cls, rx in _CARRY:
        if wanted is not None and cls not in wanted:
            continue
        for m in rx.finditer(ctx):
            phrase = _normalize(m.group(0))
            if phrase:
                hits.append((m.start(), phrase))
    hits.sort(key=lambda p: p[0])

    kept: list[str] = []
    for _pos, phrase in hits:
        low = phrase.lower()
        redundant = False
        for i, existing in enumerate(kept):
            elow = existing.lower()
            if low == elow or low in elow:
                redundant = True
                break
            if elow in low:  # new phrase is the fuller statement
                kept[i] = phrase
                redundant = True
                break
        if not redundant:
            kept.append(phrase)
    return kept[:MAX_CARRIED]


def carry(session_context: str) -> list[str]:
    """Every constraint phrase already stated in this session.

    Ordered by first appearance so the earliest standing constraint leads.
    A phrase wholly contained in a longer kept phrase is dropped, so
    "don't commit" does not shadow "don't commit until I say so".
    """
    return _collect(session_context, None)


def carry_task(session_context: str) -> list[str]:
    """Constraints on the work. These belong under Constraints."""
    return _collect(session_context, {c for c, _ in _CARRY_SPECS} - PRESENTATION_CLASSES)


def carry_presentation(session_context: str) -> list[str]:
    """Constraints on how the answer reads. These belong under Output."""
    return _collect(session_context, set(PRESENTATION_CLASSES))


def classes(session_context: str) -> list[str]:
    """Constraint classes present, for telemetry. Never returns user text."""
    ctx = session_context or ""
    found: list[str] = []
    for cls, rx in _CARRY:
        if cls not in found and rx.search(ctx):
            found.append(cls)
    return found
