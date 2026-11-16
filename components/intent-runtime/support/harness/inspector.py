"""Deterministic inspector for compiled vs naive turns.

This is the local stand-in for a post-runner review chassis. It scores
constraint survival and invention. It never stores raw user text beyond
the case id and the already-sanitized fixture fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from support.harness.compiler import compile_contract, render, route
from support.harness.shape_check import check_shape
from hooks.session_signals import detect


@dataclass
class ArmScore:
    route: str
    gaps: list[str]
    signals: list[str]
    survived: list[str]
    missing: list[str]
    invented: list[str]
    score: int
    prompt_chars: int


@dataclass
class CaseReview:
    id: str
    pattern: str
    naive: ArmScore
    compiled: ArmScore
    delta: int
    winner: str
    rating: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _hay(prompt: str, extra: dict | None = None) -> str:
    blob = prompt
    if extra:
        blob += "\n" + "\n".join(str(v) for v in extra.values())
    return blob.lower()


def _score_arm(
    message: str,
    session_context: str,
    must_survive: list[str],
    must_not_invent: list[str],
    *,
    naive: bool,
) -> ArmScore:
    if naive:
        prompt = message
        decision = route(message, executor="fork", session_context="")
        signals = detect(message, "")
        extra = {}
        prompt_chars = len(prompt)
    else:
        decision = route(message, executor="fork", session_context=session_context)
        contract = compile_contract(
            message,
            session_context=session_context,
            decision=decision,
            executor="fork",
        )
        prompt, _hints = render(contract)
        signals = detect(message, session_context)
        extra = contract.to_dict()
        prompt_chars = len(prompt)

    hay = _hay(prompt, extra)
    survived = [c for c in must_survive if c.lower() in hay]
    missing = [c for c in must_survive if c.lower() not in hay]
    invented = [c for c in must_not_invent if c.lower() in hay]
    if not naive:
        shape = check_shape(prompt)
        if not shape.ok:
            missing = missing + [f"shape:{reason}" for reason in shape.reasons]
    score = 10
    score -= 2 * len(missing)
    score -= 3 * len(invented)
    if not naive and session_context and "G1" in decision.gaps:
        # Bound work should mention recovered context, not only the outburst.
        if session_context.split("\n")[0].split(":")[-1].strip().lower()[:12] in hay:
            score += 1
    score = max(0, min(10, score))
    return ArmScore(
        route=decision.expect,
        gaps=list(decision.gaps),
        signals=signals,
        survived=survived,
        missing=missing,
        invented=invented,
        score=score,
        prompt_chars=prompt_chars,
    )


def review_case(case: dict) -> CaseReview:
    message = case["message"]
    ctx = case.get("session_context") or ""
    survive = case.get("must_survive") or []
    invent = case.get("must_not_invent") or []
    naive = _score_arm(message, ctx, survive, invent, naive=True)
    compiled = _score_arm(message, ctx, survive, invent, naive=False)
    delta = compiled.score - naive.score
    if delta > 0:
        winner = "compiled"
    elif delta < 0:
        winner = "naive"
    else:
        winner = "tie"
    if compiled.score >= 8 and delta > 0:
        rating = "strong-lift"
    elif compiled.score >= 6 and compiled.missing == []:
        rating = "pass"
    elif compiled.invented:
        rating = "invention"
    else:
        rating = "weak"
    notes = []
    if compiled.missing:
        notes.append("compiled missing: " + ", ".join(compiled.missing))
    if compiled.invented:
        notes.append("compiled invented: " + ", ".join(compiled.invented))
    if delta > 0:
        notes.append(f"compiled recovered {len(compiled.survived)} constraints naive missed")
    return CaseReview(
        id=case["id"],
        pattern=case.get("pattern") or "",
        naive=naive,
        compiled=compiled,
        delta=delta,
        winner=winner,
        rating=rating,
        notes=notes,
    )


def third_template_fails(prompt: str) -> bool:
    """AE3: a Task / Done when string is a shape fail."""
    return not check_shape(prompt).ok


def summarize(reviews: list[CaseReview]) -> dict:
    n = len(reviews)
    lifts = sum(1 for r in reviews if r.delta > 0)
    ties = sum(1 for r in reviews if r.delta == 0)
    losses = sum(1 for r in reviews if r.delta < 0)
    avg_delta = sum(r.delta for r in reviews) / n if n else 0.0
    return {
        "n": n,
        "lifts": lifts,
        "ties": ties,
        "losses": losses,
        "avg_delta": round(avg_delta, 2),
        "positive_use": lifts > losses and avg_delta > 0,
    }
