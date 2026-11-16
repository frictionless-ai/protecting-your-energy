"""Session-pattern signals shared by the compiler and the local benchmark.

These are the time-sink shapes from long agent sessions: the user already
implied a constraint, the agent missed it, and the next turn is short,
upset, or a restatement. Casual register alone is not a signal.

Pattern *strings* are the contract. Stdlib only.
"""

from __future__ import annotations

import re

# --- pattern strings ---------------------------------------------------------

# Register slang is evidence of mood, not a rewrite gap by itself.
REGISTER_PATTERN = r"\b(bro|bruh|wtf|wth|ffs|ngl|yo)\b"
FRUSTRATION_PATTERN = (
    r"\b("
    r"are you kidding|you didn'?t|you did not|"
    r"why can'?t you|what part of"
    r")\b"
)
REPEAT_PATTERN = (
    r"\b("
    r"still\s+(not|broken|failing|fail|using|doesn|don'?t|do not|seems|wrong|red)|"
    r"you'?re still|"
    r"again|none of (those|that)|"
    r"i told you|i already (said|told|asked)|"
    r"keeps failing|third time|how many times|"
    r"i said\b.{0,40}\b(not|only|just)"
    r")\b"
)
SCOPE_PUSHBACK_PATTERN = (
    r"\b("
    r"i only asked|too much|don'?t rewrite|do not rewrite|"
    r"just the one|leave the rest|"
    r"don'?t touch (anything|everything|the rest|other)"
    r")\b"
)
DO_IT_ALREADY_PATTERN = (
    r"\b("
    r"just (fix|do|make|change|ship) it|"
    r"stop asking|don'?t explain|no more questions|quit explaining|"
    r"stop (talking|planning) and"
    r")\b"
)
CORRECTION_PATTERN = (
    r"^\s*(no[,.]?\s+|not that|i meant|kill it|undo that|stop,|i don'?t want)"
)
RESTATED_CONSTRAINT_PATTERN = (
    r"\b("
    r"fedora|kde|gnome|ubuntu|debian|windows|macos|"
    r"don'?t (commit|push|ask)|do not (commit|push|ask)|"
    r"only (fedora|kde|linux|local)|no (github|remote|third[- ]party)|"
    r"audio|midi|mcp|webui|browser"
    r")\b"
)
STILL_NOT_DONE_PATTERN = (
    r"\b("
    r"still not done|you'?re still not done|not done yet|"
    r"where you left off|keep going on"
    r")\b"
)
CEREMONY_CONTINUE_PATTERN = (
    r"\b("
    r"choose the next|next (ce )?skill|pick for me|"
    r"do the next step|continue wherever you|"
    r"of your (own )?choosing|skill/command/subagent"
    r")\b"
)
VERIFY_SURFACE_PATTERN = (
    r"\b("
    r"webui|in the browser|dogfood|"
    r"confirm everything|everything and anything in the|"
    r"works properly"
    r")\b"
)
# Meta-complaint: the user is driving the agent's loop. Tight on purpose —
# bare "follow up" / "check" / "iterate" would flood the archive.
SELF_HANDHOLD_PATTERN = (
    r"\b("
    r"connect(?:ing)? the dots|"
    r"hand[- ]?hold(?:ing)?|"
    r"tired of (?:telling|asking|reminding|hand[- ]?holding|connecting)|"
    r"telling (?:it|you|the (?:agent|model)) to follow[- ]?up|"
    r"ensuring it iterates|"
    r"actually checks|"
    r"check (?:it|things) yourself|"
    r"iterate until|"
    r"stop waiting for me|"
    r"(?:have to|keep having to|shouldn'?t have to)\s+(?:keep\s+)?"
    r"(?:remind(?:ing)?\s+you|"
    r"tell(?:ing)?\s+you\s+to\s+(?:verify|check|test|confirm)|"
    r"spell(?:ing)?\s+out\b.{0,40}?\b(?:for|to)\s+(?:you|it)\b|"
    r"walk(?:ing)?\s+(?:you|it)\s+through)|"
    r"without me\s+(?:babysit(?:ting)?|remind(?:ing)?|"
    r"walk(?:ing)?\s+(?:you|it)\s+through)|"
    r"make(?:s)?\s+me\s+(?:tell|remind)\s+(?:you|it)"
    r")\b"
)
PROJECT_CONTEXT_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    "STRATEGY.md",
)

FRUSTRATION = re.compile(FRUSTRATION_PATTERN, re.I)
REPEAT = re.compile(REPEAT_PATTERN, re.I)
SCOPE_PUSHBACK = re.compile(SCOPE_PUSHBACK_PATTERN, re.I)
DO_IT_ALREADY = re.compile(DO_IT_ALREADY_PATTERN, re.I)
CORRECTION = re.compile(CORRECTION_PATTERN, re.I)
RESTATED_CONSTRAINT = re.compile(RESTATED_CONSTRAINT_PATTERN, re.I)
STILL_NOT_DONE = re.compile(STILL_NOT_DONE_PATTERN, re.I)
CEREMONY_CONTINUE = re.compile(CEREMONY_CONTINUE_PATTERN, re.I)
VERIFY_SURFACE = re.compile(VERIFY_SURFACE_PATTERN, re.I)
SELF_HANDHOLD = re.compile(SELF_HANDHOLD_PATTERN, re.I)

# G5 is a missed-point restatement. hello? is a ping, not a word-boundary token.
# Register slang stays out so "wtf is X?" is still a complete question.
G5_PATTERN = (
    r"("
    + FRUSTRATION_PATTERN
    + r"|"
    + REPEAT_PATTERN
    + r"|"
    + STILL_NOT_DONE_PATTERN
    + r"|"
    + SELF_HANDHOLD_PATTERN
    + r"|hello\?"
    + r")"
)
G5_SIGNAL = re.compile(G5_PATTERN, re.I)
REGISTER = re.compile(REGISTER_PATTERN, re.I)

_CONSTRAINT_LINE = re.compile(
    r"(?im)^(?:[-*]\s*)?((?:only |use |on |running )?"
    r"(?:fedora|kde|gnome|ubuntu|debian|windows|macos|linux|audio|midi|mcp)"
    r"[^\n]{0,80}|"
    r"(?:don'?t|do not)\s+(?:commit|push|ask|rewrite|touch)[^\n]{0,80}|"
    r"(?:verify|dogfood|browser|webui)[^\n]{0,80})"
)


def detect(message: str, session_context: str = "") -> list[str]:
    """Return ordered unique signal names for this turn."""
    text = message or ""
    ctx = session_context or ""
    found: list[str] = []

    def add(name: str) -> None:
        if name not in found:
            found.append(name)

    if FRUSTRATION.search(text) or (REGISTER.search(text) and ctx):
        add("frustration")
    if REPEAT.search(text):
        add("repeat_ask")
    if CORRECTION.match(text.strip()):
        add("correction")
    if SCOPE_PUSHBACK.search(text):
        add("scope_pushback")
    if DO_IT_ALREADY.search(text):
        add("do_it_already")
    if RESTATED_CONSTRAINT.search(text) and ctx:
        add("restated_constraint")
    if STILL_NOT_DONE.search(text):
        add("still_not_done")
    if CEREMONY_CONTINUE.search(text):
        add("ceremony_continue")
    if VERIFY_SURFACE.search(text):
        add("verify_surface")
    if SELF_HANDHOLD.search(text):
        add("self_handhold")
    if (
        FRUSTRATION.search(text)
        or REPEAT.search(text)
        or STILL_NOT_DONE.search(text)
        or CEREMONY_CONTINUE.search(text)
        or SELF_HANDHOLD.search(text)
    ) and ctx:
        add("missed_inference")
    return found


def has_g5(message: str) -> bool:
    return bool(G5_SIGNAL.search(message or ""))


def _carried(ctx: str) -> list[str]:
    """Bridge to constraint_carry under both package and direct-path import."""
    try:
        from hooks.constraint_carry import carry_task as carry
    except ImportError:  # loaded by path, no package context
        try:
            from constraint_carry import carry_task as carry  # type: ignore
        except ImportError:
            return []
    return carry(ctx)


def lift_constraints(session_context: str) -> list[str]:
    """Promote already-stated env/negation facts so a short follow-up keeps them."""
    ctx = session_context or ""
    out: list[str] = []
    seen: set[str] = set()
    for match in _CONSTRAINT_LINE.finditer(ctx):
        phrase = " ".join(match.group(1).split())
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(phrase)
    # Line anchoring above misses constraints stated mid-sentence, which the
    # archive shows is where most of them are. constraint_carry reads anywhere
    # in the context; the union keeps line-anchored hits first.
    for phrase in _carried(ctx):
        key = phrase.lower()
        if key in seen or any(key in s for s in seen):
            continue
        seen.add(key)
        out.append(phrase)
    return out[:10]


# A concrete target means the ask is not vague. Blind CLI grading showed the
# standing-doc list read as unrequested scope when the user had already named
# the file to change.
_CONCRETE_TARGET = re.compile(
    r"(?:^|\s)[\w./-]+/[\w.-]+"
    r"|\b[\w-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|sh|ya?ml|json|toml|md|c|h|cpp)\b",
    re.I,
)


def project_context_paths(message: str) -> list[str]:
    """Name standing repo files to read when the ask is vague, not their text."""
    text = message or ""
    if not text.strip():
        return []
    if len(text.split()) > 40 and not has_g5(text):
        return []
    # The user already pointed at the thing. Do not widen the read surface.
    if _CONCRETE_TARGET.search(text) and not has_g5(text):
        return []
    return list(PROJECT_CONTEXT_PATHS)
