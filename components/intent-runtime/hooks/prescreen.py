"""Deterministic pre-screen shared by the hook and the heuristic compiler.

Pattern *strings* are the contract: if a caller keeps a local copy, tests
assert those copies stay equal to the values here.
"""

from __future__ import annotations

import re

# --- pattern strings (single source of truth) --------------------------------

SLASH_PATTERN = r"^\s*/\S"
RAW_PATH_PATTERN = r"^\s*(~?/|\./)\S+\s*$"
# First-token filter only. is_raw_shell() applies English / command-like rules.
RAW_SHELL_PATTERN = (
    r"^\s*(?:sudo\s+)?(?:"
    r"(?:cd|ls|cat|git|python3?|pip3?|npm|npx|cargo|docker|kubectl|ssh|curl|wget|"
    r"rm|mv|cp|chmod|chown|shred|dd)\b"
    r"|make\s+(?!the\b|a\b|an\b|my\b|our\b|it\b|this\b|that\b|them\b|me\b|sure\b)\S"
    r")"
)
OPTOUT_PATTERN = (
    r"(stop|don'?t|do not|quit)\s+"
    r"(rewriting|uplifting|optimi[sz]ing|rewrite|uplift|optimi[sz]e)\s+"
    r"(my\s+)?(prompts?|messages?)"
)
AUTONOMY_PATTERN = (
    r"\b("
    r"just do it(?: all)?"
    r"|don'?t ask me"
    r"|you have permission"
    r"|use your best judgement"
    r"|full permission granted"
    r"|proceed"
    r")\b"
)

SLASH = re.compile(SLASH_PATTERN)
RAW_PATH = re.compile(RAW_PATH_PATTERN)
RAW_SHELL = re.compile(RAW_SHELL_PATTERN)
OPTOUT = re.compile(OPTOUT_PATTERN, re.IGNORECASE)
AUTONOMY = re.compile(AUTONOMY_PATTERN, re.IGNORECASE)

_GIT_SUBCOMMANDS = {
    "status",
    "add",
    "commit",
    "push",
    "pull",
    "checkout",
    "branch",
    "log",
    "diff",
    "merge",
    "rebase",
    "stash",
    "fetch",
    "clone",
    "init",
    "remote",
    "reset",
    "tag",
    "show",
    "blame",
    "cherry-pick",
    "switch",
    "restore",
    "config",
    "help",
    "version",
    "mv",
    "rm",
    "bisect",
    "worktree",
    "submodule",
    "stash",
}
_MAKE_ENGLISH = {
    "the",
    "a",
    "an",
    "my",
    "our",
    "it",
    "this",
    "that",
    "them",
    "me",
    "sure",
}
_SHELL_HEADS = {
    "cd",
    "ls",
    "cat",
    "git",
    "python",
    "python3",
    "pip",
    "pip3",
    "npm",
    "npx",
    "cargo",
    "docker",
    "kubectl",
    "ssh",
    "curl",
    "wget",
    "make",
    "rm",
    "mv",
    "cp",
    "chmod",
    "chown",
    "sudo",
    "shred",
    "dd",
}
_AUTONOMY_STRIP = (
    r"you have permission",
    r"full permission granted",
    r"just hurry up and do it all",
    r"just do it all",
    r"just do it",
    r"don'?t ask me(?: every five minutes)?",
    r"use your best judgement",
    r"\bproceed\b",
    r"hurry up",
    r"and do it all",
)

_INTERROGATIVE_PREFIX = re.compile(
    r"^\s*(how\s+(do|can|should|would)\s+i|how\s+to)\b",
    re.IGNORECASE,
)
# Cursor / Claude export wrappers. Classification sees the inner turn.
HARNESS_TAG = re.compile(
    r"</?(?:user_query|timestamp|system_notification|"
    r"manually_attached_skills|subagent_delegation_context|"
    r"user_visible_high_level_summary|image_asset_pointer|"
    r"turn_aborted)(?:\s[^>]*)?>",
    re.IGNORECASE,
)


def unwrap_harness(text: str) -> str:
    """Return the inner user turn when a host wrapped it in known tags."""
    cleaned = HARNESS_TAG.sub(" ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _inside_quotes(text: str, start: int, end: int) -> bool:
    """True when [start:end] sits inside a quoted span."""
    for q in ('"', "'", "\u201c", "\u201d"):
        before = text.rfind(q, 0, start)
        if before == -1:
            continue
        after = text.find(q, end)
        if after != -1:
            return True
    # paired curly quotes
    if text.rfind("\u201c", 0, start) != -1 and text.find("\u201d", end) != -1:
        return True
    return False


def optout_kind(text: str) -> str | None:
    """Return 'sticky', 'quoted', 'interrogative', or None."""
    match = OPTOUT.search(text)
    if not match:
        return None
    if _INTERROGATIVE_PREFIX.search(text) or (
        re.search(r"\bhow\s+(do|can|should|would)\s+i\b", text[: match.start() + 1], re.I)
        and "?" in text
    ):
        return "interrogative"
    if _inside_quotes(text, match.start(), match.end()):
        return "quoted"
    return "sticky"


def is_sticky_optout(text: str) -> bool:
    return optout_kind(text) == "sticky"


def is_quoted_optout(text: str) -> bool:
    return optout_kind(text) == "quoted"


def is_interrogative_optout(text: str) -> bool:
    return optout_kind(text) == "interrogative"


def _looks_like_sentence(text: str) -> bool:
    if re.search(r"[|&;><]|[ \t]-{1,2}\w", text):
        return False
    words = text.split()
    if len(words) >= 6 and text.rstrip().endswith("."):
        return True
    return False


def is_raw_shell(text: str) -> bool:
    """True for a command-like shell line that must pass through unmarked.

    English ``make the/a/an/my/our …`` is not make(1). ``git keeps rejecting
    my push`` is not git(1). Destructive command-like lines (``rm -rf``) *are*
    pass-through — they are not uplift candidates. A ``?`` or a sentence
    shape is not a command.
    """
    stripped = text.strip()
    if not stripped or "?" in stripped:
        return False
    if not RAW_SHELL.match(stripped):
        # Bare ls/git/make as the whole line: still protected.
        if stripped in _SHELL_HEADS:
            return True
        return False
    first, *rest = stripped.split(None, 1)
    if first == "sudo" and rest:
        return is_raw_shell(rest[0])
    if first == "make" and rest:
        nxt = rest[0].split()[0].lower()
        if nxt in _MAKE_ENGLISH:
            return False
    if first == "git":
        if not rest:
            return True
        nxt = rest[0].split()[0].lower()
        if nxt.startswith("-"):
            return True
        if nxt not in _GIT_SUBCOMMANDS:
            return False
    if _looks_like_sentence(stripped):
        return False
    return True


def is_slash(text: str) -> bool:
    """True for a bare slash command. A command plus an English job is not protected.

    `/help`, `/lfg`, and `/ce-plan` stay pass-through. `/lfg keep going on
    the audio` and `/browser-automation confirm the webui` are tasks.
    """
    stripped = text.strip()
    if not SLASH.match(stripped):
        return False
    rest = re.sub(r"^\s*/[\w.:-]+", "", stripped).strip()
    if not rest:
        return True
    for tok in rest.split():
        if tok.startswith("-"):
            continue
        if "=" in tok and not re.search(r"[.!?]", tok):
            continue
        return False
    return True


def is_raw_path(text: str) -> bool:
    return bool(RAW_PATH.match(text.strip()))


def is_autonomy_grant_only(text: str) -> bool:
    """True when the turn is only an autonomy grant, not a task + grant."""
    if not AUTONOMY.search(text):
        return False
    residual = text
    for pattern in _AUTONOMY_STRIP:
        residual = re.sub(pattern, " ", residual, flags=re.IGNORECASE)
    residual = re.sub(r"[.,;:…!?]+", " ", residual)
    residual = re.sub(r"\s+", " ", residual).strip()
    return len(residual) < 12


_LABELED_SPEC = re.compile(r"\boutcome\b.*\bconstraint", re.I | re.S)
_LABELED_CHECK = re.compile(r"\bcheck\b", re.I)
_SPEC_ARTIFACT = re.compile(
    r"(?:[\w.-]+\.(?:py|md|ts|js|toml)|scripts/|--[a-z][\w-]*)",
    re.I,
)
_SPEC_CONSTRAINT = re.compile(
    r"\b(?:must not|do not change|don't change|when omitted|without changing)\b",
    re.I,
)
_SPEC_CHECK = re.compile(
    r"\b(?:add a unittest|add a (?:unit )?test|unittest that|verify that)\b",
    re.I,
)


def looks_already_complete(text: str) -> bool:
    """True when the turn already names an outcome, a constraint, and a check."""
    raw = text or ""
    if _LABELED_SPEC.search(raw) and _LABELED_CHECK.search(raw):
        return True
    return bool(
        _SPEC_ARTIFACT.search(raw)
        and _SPEC_CONSTRAINT.search(raw)
        and _SPEC_CHECK.search(raw)
    )


def is_protected(text: str) -> bool:
    """Deterministic pass-through classes (slash / path / shell / opt-out / grant)."""
    stripped = unwrap_harness(text)
    if not stripped:
        return True
    if is_slash(stripped) or is_raw_path(stripped) or is_raw_shell(stripped):
        return True
    if is_sticky_optout(stripped):
        return True
    if is_autonomy_grant_only(stripped):
        return True
    return False
