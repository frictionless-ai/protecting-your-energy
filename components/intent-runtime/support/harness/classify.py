"""Deterministic classify + expansion used by merge conformance tests."""

from __future__ import annotations

import re

from hooks.prescreen import (
    is_raw_path,
    is_raw_shell,
    is_slash,
    looks_already_complete,
    optout_kind,
)

_SKIP_ACK = re.compile(r"^\s*(thanks|thank you|ok|okay|lgtm|sounds good)\s*[.!]?\s*$", re.I)
_MISSION = re.compile(
    r"("
    r"\bmake (this|it|the \w+) (reliable|production-ready|solid)\b"
    r"|\bget (this|it) production-ready\b"
    r"|\btake ownership\b"
    r"|\bclean up this codebase\b"
    r"|\bstart a mission\b"
    r"|\bstill not done\b"
    r"|\bchoose the next\b"
    r"|\bpick for me\b"
    r"|\bhand[- ]?hold"
    r"|\bconnect(?:ing)? the dots\b"
    r")",
    re.I,
)
_RUNTIME_SLASH = re.compile(
    r"^\s*/intent-runtime\b",
    re.I,
)


def classify(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "skip"
    if _RUNTIME_SLASH.match(text) or _MISSION.search(text):
        return "mission"
    if is_slash(text) or is_raw_path(text) or is_raw_shell(text):
        return "skip"
    if optout_kind(text):
        return "skip"
    if _SKIP_ACK.match(text):
        return "skip"
    if looks_already_complete(text):
        return "skip"
    return "task"


def expansion(message: str, adjacent_fragile: bool) -> str:
    """none unless omitting neighbors would leave the change inconsistent."""
    if classify(message) == "skip":
        return "none"
    if adjacent_fragile:
        return "entailed"
    return "none"
