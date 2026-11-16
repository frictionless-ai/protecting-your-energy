"""Shared compile-spec skeleton check.

The heading list is the compile-spec Template. This module is the no-model
double of the pre-dispatch check. It stores no raw user text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADINGS = (
    "Objective",
    "Why",
    "Recovered context",
    "Constraints",
    "Scope",
    "Non-goals",
    "Evidence",
    "Output",
    "Assumptions",
    "Chassis",
)

NA_WHY = "n/a — does not change the work"
NA_GENERIC = "n/a"

_HEADING_RE = re.compile(r"^## (.+)$", re.M)
# ReAct scaffolding only counts when it leads a line. Unanchored, "action:\s"
# also matched the skeleton's own "Requested action:" field and failed every
# compiled prompt.
_RITUAL = re.compile(
    r"\b(?:think step by step|think hard|ultrathink)\b"
    r"|^[ \t]*(?:thought|action|observation):[ \t]",
    re.I | re.M,
)
_CONVERSATION_POINTER = re.compile(
    r"\b(the conversation above|conversation above|as discussed above)\b",
    re.I,
)
_PRESENTATION_IN_CONSTRAINTS = re.compile(
    r"\b(plain english|less writing|no intro|show them as a table|don't sound like ai)\b",
    re.I,
)
_CLASS_WRAPPER = re.compile(r"^\s*(class |def )\w+", re.M)


@dataclass(frozen=True)
class ShapeResult:
    ok: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"ok": self.ok, "reasons": list(self.reasons)}


def _section_bodies(prompt: str) -> dict[str, str]:
    found: dict[str, str] = {}
    matches = list(_HEADING_RE.finditer(prompt))
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
        found[name] = prompt[start:end].strip()
    return found


def check_shape(prompt: str) -> ShapeResult:
    reasons: list[str] = []
    bodies = _section_bodies(prompt)
    for heading in HEADINGS:
        body = bodies.get(heading, "")
        if heading not in bodies:
            reasons.append(f"missing heading: {heading}")
        elif not body:
            reasons.append(f"empty heading: {heading}")
    if "Task" in bodies or "Done when" in bodies or "Context" in bodies:
        reasons.append("third-template heading")
    recovered = bodies.get("Recovered context", "")
    objective = bodies.get("Objective", "")
    if "<recovered>" in objective or re.search(r"(?m)^User:", objective):
        reasons.append("recovered text in Objective")
    if recovered:
        facts = [
            line[2:].strip()
            for line in recovered.splitlines()
            if line.startswith("- ")
        ]
        wrapped = re.search(r"<recovered>(.*)</recovered>", recovered, re.S)
        inner = wrapped.group(1) if wrapped else ""
        for fact in facts:
            if fact and fact not in inner:
                reasons.append("recovered text outside XML")
                break
        if facts and not wrapped:
            reasons.append("recovered text outside XML")
    for heading, body in bodies.items():
        if heading != "Recovered context" and "<recovered>" in body:
            reasons.append("recovered XML outside Recovered context")
            break
    constraints = bodies.get("Constraints", "")
    if constraints and _PRESENTATION_IN_CONSTRAINTS.search(constraints):
        reasons.append("presentation in Constraints")
    for heading, body in bodies.items():
        if heading == "Constraints":
            continue
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and "[negations]" in stripped:
                if "<negation>" not in body:
                    reasons.append("negation outside XML")
                    break
    if _RITUAL.search(prompt):
        reasons.append("reasoning ritual")
    if _CONVERSATION_POINTER.search(prompt):
        reasons.append("conversation pointer")
    if _CLASS_WRAPPER.search(prompt):
        reasons.append("class or function wrapper")
    return ShapeResult(ok=not reasons, reasons=tuple(reasons))
