"""Heuristic compiler that follows SKILLS.md Rev. 2 enough to be testable.

This is not a substitute for the live Fable-5 skill. It exists so CI can
assert routing, contract invariants, portable-base rendering, and the
subagent isolation contract without calling a model.
"""

from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hooks.prescreen import (  # noqa: E402
    AUTONOMY,
    OPTOUT,
    RAW_PATH,
    RAW_SHELL,
    SLASH,
    is_autonomy_grant_only,
    is_raw_path,
    is_raw_shell,
    is_slash,
    is_sticky_optout,
    looks_already_complete,
    unwrap_harness,
)
from support.harness.shape_check import (  # noqa: E402
    NA_GENERIC,
    NA_WHY,
    check_shape,
)
from hooks.constraint_carry import carry_presentation as _carried_presentation  # noqa: E402
from hooks.session_signals import (  # noqa: E402
    CEREMONY_CONTINUE,
    DO_IT_ALREADY,
    G5_SIGNAL,
    SCOPE_PUSHBACK,
    VERIFY_SURFACE,
    detect as detect_session_signals,
    lift_constraints,
    project_context_paths,
)

CONTINUATION = re.compile(
    r"^\s*(yes[,.]?\s+)?("
    r"continue(\s+[\w][\w./:-]*){0,3}"
    r"|try again"
    r"|go (for it|ahead)"
    r"|confirm"
    r"|whatever you deem appropriate"
    r"|implement (the |this |that )?plan"
    r"|(do )?any remaining work"
    r")\.?\s*$",
    re.I,
)
CORRECTION = re.compile(
    r"^\s*(no[,.]?\s+|not that|i meant|kill it|undo that|stop,|i don't want)",
    re.I,
)
CONSTRAINT_LEADING = re.compile(
    r"^\s*(don'?t|do not)\s+use\b.+\bwhen you\b",
    re.I,
)
REFERENT = re.compile(r"\b(it|this|that|the thing|the one|both|them)\b", re.I)
VAGUE_GOAL = re.compile(
    r"\b(improve|better|tidy|cleanup|clean up|clean this|polish|fix this|"
    r"make it|make the|make this|gen(erate)?\s+\d+)\b",
    re.I,
)
ANSWER_MODE = re.compile(
    r"\b("
    r"tell me|explain|how\s+(do|would|can|to)|"
    r"what\s+(is|does|are|did)|why|"
    r"review|does this look|thoughts|summarize|"
    r"calculate|compute|compare"
    r")\b",
    re.I,
)
CHANGE_MODE = re.compile(
    r"\b(fix|change|migrate|implement|port|rename|delete|write the code|make the change)\b",
    re.I,
)
GENERATE_MODE = re.compile(
    r"\b(generate|gen|write|create|produce|draft|come up with|translate|turn\b.+\binto)\b",
    re.I,
)
NEGATION = re.compile(
    r"\b("
    r"don'?t|do not|never|"
    r"no\s+(kill it|third-party|code comments|essays?)|"
    r"without ads|avoid "
    r")\b[\w\s/-]{0,40}",
    re.I,
)
PERSIST = re.compile(r"\b(from now on|always|for the rest of this session|stop doing)\b", re.I)
ARTIFACT_PLACEHOLDER = re.compile(r"\[(?:pasted|attached|image)[^\]]*\]", re.I)
G6_ENV = re.compile(
    r"\b("
    r"here|my gpu|the other machine|like we discussed|"
    r"x server|compose file|same error|install it globally|build here"
    r")\b",
    re.I,
)
G7_SCOPE = re.compile(
    r"\b("
    r"fully|rewrite|reverse engineer|cross-platform|end[- ]to[- ]end|"
    r"whole monolith|the entire|the works|production ready|decompile the full"
    r")\b",
    re.I,
)
OUTPUT_SHAPE = re.compile(r"\b(just the|one[- ]liner|shortly|no essay|be concise|json)\b", re.I)
STATED_MOTIVE = re.compile(
    r"\b(because|so that|i need this because)\b.{0,80}",
    re.I,
)

# Exact snapshot lookup — never startswith family inference.
SNAPSHOT_HINTS: dict[str, dict] = {
    "claude-fable-5": {"effort": "high"},
    "gpt-5.6-sol": {"effort": "medium", "verbosity": "medium"},
    "gpt-5.6-terra": {"effort": "medium", "verbosity": "medium"},
    "gpt-5.6-luna": {"effort": "medium", "verbosity": "medium"},
}


@dataclass
class Route:
    expect: str
    reasons: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    klass: str | None = None


@dataclass
class ExecutionContract:
    objective: str = ""
    requested_action: str = ""
    deliverable: str = ""
    relevant_context: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    previous_failures: list[str] = field(default_factory=list)
    hard_constraints: list[str] = field(default_factory=list)
    negations: list[str] = field(default_factory=list)
    authority_granted: list[str] = field(default_factory=list)
    authority_not_granted: list[str] = field(default_factory=list)
    response_contract: list[str] = field(default_factory=list)
    success_conditions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unresolved_ambiguities: list[str] = field(default_factory=list)
    irreversible_or_external_actions: list[str] = field(default_factory=list)
    inferred_intent: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _strip_artifacts(text: str) -> str:
    cleaned = ARTIFACT_PLACEHOLDER.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _has_artifact(text: str) -> bool:
    if ARTIFACT_PLACEHOLDER.search(text):
        return True
    return text.count("\n") >= 8 or len(text) > 800


def _is_correction(text: str) -> bool:
    if is_sticky_optout(text):
        return False
    if CONSTRAINT_LEADING.search(text):
        return False
    return bool(CORRECTION.match(text))


def _no_pending_task(session_context: str) -> bool:
    return bool(re.search(r"no pending task", session_context, re.I))


def route(message: str, executor: str = "fork", session_context: str = "") -> Route:
    text = unwrap_harness(message)
    # Opt-out before G2/correction. Quoted/interrogative opt-out is not protected.
    if is_slash(text) or is_raw_path(text) or is_raw_shell(text) or is_sticky_optout(text):
        return Route(expect="pass", reasons=["protected"], klass="protected")
    if is_autonomy_grant_only(text):
        return Route(expect="pass", reasons=["protected"], klass="protected")
    if looks_already_complete(text):
        return Route(expect="pass", reasons=["complete"], klass="complete")

    gaps: list[str] = []
    reasons: list[str] = []
    ctx = session_context.strip()

    if CONTINUATION.match(text):
        if executor == "self":
            return Route(expect="pass", reasons=["complete"], klass="delegation-self")
        if _no_pending_task(ctx):
            return Route(expect="pass", reasons=["complete"], klass="complete")
        if not ctx:
            # I5: unbound G1-only with nothing to bind → pass through.
            return Route(expect="pass", reasons=["complete"], klass="complete")
        gaps.append("G1")
        reasons.append("needs-context-expansion")
    elif REFERENT.search(text) and executor == "fork":
        if ctx:
            gaps.append("G1")
            reasons.append("needs-context-expansion")
        else:
            # Unbound referent and no bindable context. If this would be the
            # only gap, pass through (I5). Other gaps below may still uplift.
            pass

    if _is_correction(text):
        gaps.append("G2")
        reasons.append("correction")

    if _has_artifact(text):
        gaps.append("G3")
        reasons.append("needs-artifact-framing")

    instruction = _strip_artifacts(text)
    if VAGUE_GOAL.search(instruction) and not re.search(
        r"\b(done when|must include|success)\b", instruction, re.I
    ):
        gaps.append("G4")
        reasons.append("needs-task-clarification")

    if G5_SIGNAL.search(instruction):
        gaps.append("G5")

    if SCOPE_PUSHBACK.search(instruction):
        if "G2" not in gaps:
            gaps.append("G2")
        reasons.append("scope-pushback")

    if DO_IT_ALREADY.search(instruction) and ctx:
        if "G5" not in gaps:
            gaps.append("G5")
        reasons.append("do-it-already")

    if CEREMONY_CONTINUE.search(instruction):
        if "G7" not in gaps:
            gaps.append("G7")
        reasons.append("ceremony-continue")

    if VERIFY_SURFACE.search(instruction):
        if "G4" not in gaps:
            gaps.append("G4")
        reasons.append("verify-surface")

    # G6 is an environment-fact gap in the *message*, not "session_context
    # happened to be attached on fork".
    if executor == "fork" and G6_ENV.search(instruction):
        if "G6" not in gaps:
            gaps.append("G6")
            if "needs-context-expansion" not in reasons:
                reasons.append("needs-context-expansion")

    if G7_SCOPE.search(instruction):
        gaps.append("G7")
        reasons.append("needs-scope-normalization")

    # G8 is a channel annotation, not an uplift gap.

    # Unbound G1-only (referent, no context, no other gap) → pass.
    if (
        not gaps
        and executor == "fork"
        and REFERENT.search(text)
        and not ctx
        and not CONTINUATION.match(text)
    ):
        return Route(expect="pass", reasons=["complete"], klass="complete")

    seen: set[str] = set()
    gaps = [g for g in gaps if not (g in seen or seen.add(g))]
    seen_r: set[str] = set()
    reasons = [r for r in reasons if not (r in seen_r or seen_r.add(r))]

    if not gaps:
        return Route(expect="pass", reasons=["complete"], klass="complete")
    return Route(expect="uplift", reasons=reasons or ["needs-context-expansion"], gaps=gaps)


def _inherit_mode(session_context: str) -> str:
    ctx = session_context.strip()
    if not ctx:
        return "unspecified"
    if re.search(r"\b(explain|explanation|answer|review|told|read-only)\b", ctx, re.I):
        return "answer"
    if re.search(r"\b(pending task|finish|implement|fix|change|migrate)\b", ctx, re.I):
        return "change"
    return "unspecified"


def _action_mode(message: str, session_context: str = "") -> str:
    if re.search(r"\bhow\s+to\s+fix\b", message, re.I):
        return "answer"
    if ANSWER_MODE.search(message):
        return "answer"
    if re.search(
        r"\b(what's wrong|wtf is wrong|diagnose|debug|why\s+(is|does|won't)|infinite loop)\b",
        message,
        re.I,
    ):
        return "diagnose"
    if CHANGE_MODE.search(message):
        return "change"
    if GENERATE_MODE.search(message):
        return "generate"
    if VAGUE_GOAL.search(message):
        return "change"
    if CONTINUATION.match(message.strip()):
        return _inherit_mode(session_context)
    return "unspecified"


def _extract_artifacts(text: str) -> list[str]:
    found = [m.group(0) for m in ARTIFACT_PLACEHOLDER.finditer(text)]
    if text.count("\n") >= 8 or len(text) > 800:
        found.append("(large pasted dump)")
    # de-dupe
    seen: set[str] = set()
    out: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _extract_instruction(text: str) -> str:
    cleaned = _strip_artifacts(text)
    if cleaned:
        return cleaned[:240]
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in reversed(lines):
        if len(ln) < 120 and not ARTIFACT_PLACEHOLDER.search(ln):
            return ln[:240]
    return (lines[0] if lines else text)[:240]


def _restate_short(text: str) -> str:
    t = text.strip().rstrip("?.!")
    return re.sub(r"\b(it|this|that)\b", "the referent", t, count=1, flags=re.I)


def _strip_output_shape_leadin(text: str) -> str:
    return re.sub(
        r"^\s*(quickly and shortly|quickly|shortly|be concise|just the one[- ]liner),\s*",
        "",
        text,
        flags=re.I,
    ).strip()


def _ambiguous_destructive(session_context: str) -> bool:
    return bool(
        re.search(r"\b(two|both|plausible|does not disambiguate)\b", session_context, re.I)
    )


def compile_contract(
    message: str,
    session_context: str = "",
    decision: Route | None = None,
    executor: str = "fork",
) -> ExecutionContract:
    decision = decision or route(message, executor=executor, session_context=session_context)
    contract = ExecutionContract()
    text = unwrap_harness(message)
    instruction = _extract_instruction(text)
    artifacts = _extract_artifacts(text)
    contract.artifacts = artifacts

    # Action mode and irreversible flags come from the instruction, never the
    # artifact blob.
    mode = _action_mode(instruction, session_context=session_context)
    if artifacts and re.search(r"\b(delete|drop|destroy|overwrite)\b", "".join(artifacts), re.I):
        # ignore destructive verbs that live only inside the dump
        pass
    contract.requested_action = mode

    ctx = session_context.strip()
    if ctx and (CONTINUATION.match(text) or (REFERENT.search(text) and len(text) < 80)):
        bound = ctx.split("\n")[0][:180]
        if CONTINUATION.match(text):
            contract.objective = bound[:240]
        else:
            contract.objective = f"{_restate_short(instruction)} ({bound})"[:240]
    else:
        contract.objective = _strip_output_shape_leadin(instruction)[:240]

    if mode == "generate":
        contract.deliverable = "the generated artifact the user asked for"
    elif mode == "answer":
        contract.deliverable = "an explanation or recommendation, not a repo change"
    elif mode == "change":
        contract.deliverable = "the requested change applied"
    elif mode == "diagnose":
        contract.deliverable = "a diagnosis of the stated problem"
    else:
        contract.deliverable = "the user's request, without inventing a pending task"

    if ctx:
        contract.relevant_context.append(ctx)

    if decision.expect == "uplift" and "G1" in decision.gaps and not ctx:
        contract.unresolved_ambiguities.append(
            "referent is unbound; do not invent a pending task"
        )
        if mode in ("change", "unspecified"):
            contract.deliverable = "the user's request, without inventing a pending task"

    if CONTINUATION.match(text) and not ctx:
        contract.unresolved_ambiguities.append(
            "no bindable antecedent; do not invent a pending task"
        )
        contract.deliverable = "the user's request, without inventing a pending task"

    if "G2" in decision.gaps:
        if not contract.requested_action.endswith("(supersedes prior instruction)"):
            contract.requested_action = f"{mode} (supersedes prior instruction)"
        if re.search(r"\b(no\s+)?kill it\b", instruction, re.I):
            if "no kill it" not in contract.negations:
                contract.negations.append("no kill it")

    for match in NEGATION.finditer(instruction):
        phrase = " ".join(match.group(0).split())
        if phrase not in contract.negations:
            contract.negations.append(phrase)

    if re.search(r"\bdon't modify anything\b", instruction, re.I):
        contract.authority_not_granted.append("don't modify anything")
        if "don't modify anything" not in contract.hard_constraints:
            contract.hard_constraints.append("don't modify anything")
        if "file modification" not in contract.authority_not_granted:
            contract.authority_not_granted.append("file modification")

    if AUTONOMY.search(instruction) and not is_autonomy_grant_only(text):
        contract.authority_granted.append(
            "proceed without per-step confirmation (user autonomy grant)"
        )
    elif AUTONOMY.search(instruction):
        # Grant-only still records the policy if someone compiles it.
        contract.authority_granted.append(
            "proceed through all phases without per-step confirmation"
        )

    if re.search(r"\buse your best judgement\b", instruction, re.I):
        if not any("best judgement" in a for a in contract.authority_granted):
            contract.authority_granted.append(
                "choose on the user's behalf ('use your best judgement')"
            )

    if OUTPUT_SHAPE.search(instruction) or re.search(
        r"\b(json|one[- ]liner|shortly|be concise|no essay)\b", instruction, re.I
    ):
        contract.response_contract.append("honor the user's stated output shape")

    # A presentation preference stated earlier in the session is still in force.
    # It renders under Output, never under Constraints.
    for phrase in _carried_presentation(session_context):
        if phrase not in contract.response_contract:
            contract.response_contract.append(phrase)

    if PERSIST.search(instruction):
        contract.assumptions.append("constraint uses explicit persistence language")

    if "G4" in decision.gaps:
        contract.success_conditions.append(
            "(assumption) output is specific enough to use without another clarification round"
        )
        contract.assumptions.append(
            "success conditions were not stated; treat 'usable on first try' as a working definition of done"
        )

    if re.search(r"\b(clean|tidy|cleanup|clean up)\b", instruction, re.I):
        contract.assumptions.append("behavior-preservation as the default reading")

    # G7: do not invent "stage internally…" as a user-stated success condition.
    if "G7" in decision.gaps:
        contract.assumptions.append(
            "long-horizon scope: stage internally; pause only for irreversible work or user-only information"
        )

    signals = detect_session_signals(instruction, ctx)
    contract.inferred_intent = {
        "direct_ask": contract.objective,
        "adjacent_impact": "",
        "recommended_cohesive_scope": "",
        "risks_if_partial": "",
        "expansion": "none",
        "session_signals": signals,
    }
    if signals:
        contract.inferred_intent["adjacent_impact"] = (
            "already-stated environment, toolchain, and negations must stay bound"
        )
        contract.inferred_intent["recommended_cohesive_scope"] = (
            "the current slice plus the recovered constraints; no new product"
        )
        contract.inferred_intent["risks_if_partial"] = (
            "dropping a recovered constraint repeats the miss and another user turn"
        )

    if "G5" in decision.gaps or "missed_inference" in signals:
        if not contract.previous_failures:
            contract.previous_failures.append(
                "prior attempt missed the user's point (neutralized)"
            )

    for fact in lift_constraints(ctx):
        if fact not in contract.hard_constraints:
            contract.hard_constraints.append(fact)
        if fact.lower() not in (c.lower() for c in contract.relevant_context):
            contract.relevant_context.append(fact)

    for path in project_context_paths(instruction):
        note = f"{path} — read before acting"
        if note not in contract.relevant_context:
            contract.relevant_context.append(note)

    if "scope_pushback" in signals:
        fence = "do not expand past the named slice"
        if fence not in contract.authority_not_granted:
            contract.authority_not_granted.append(fence)
        if fence not in contract.hard_constraints:
            contract.hard_constraints.append(fence)

    if "do_it_already" in signals:
        grant = "proceed without another clarification round"
        if grant not in contract.authority_granted:
            contract.authority_granted.append(grant)
        if contract.requested_action == "unspecified":
            contract.requested_action = "change"

    if "ceremony_continue" in signals:
        grant = "pick the next skill and continue; do not ask which one"
        if grant not in contract.authority_granted:
            contract.authority_granted.append(grant)
        miss = "prior stop after one skill or one unit (neutralized)"
        if miss not in contract.previous_failures:
            contract.previous_failures.append(miss)

    if "verify_surface" in signals or "still_not_done" in signals:
        check = (
            "observable UI or audio check (browser, dogfood, or replay), "
            "not a narration of done"
        )
        if check not in contract.success_conditions:
            contract.success_conditions.append(check)
        if "verify_surface" in signals:
            contract.inferred_intent["adjacent_impact"] = (
                "MCP writes and the studio UI must stay consistent"
            )

    if "self_handhold" in signals:
        grant = "connect recovered facts; generate follow-ups; iterate until an observable check; do not hand the loop to the user"
        if grant not in contract.authority_granted:
            contract.authority_granted.append(grant)
        check = "observable check the agent runs, not a request that the user verify"
        if check not in contract.success_conditions:
            contract.success_conditions.append(check)
        miss = "user had to drive connect-dots, follow-up, iterate, or check (neutralized)"
        if miss not in contract.previous_failures:
            contract.previous_failures.append(miss)
        contract.inferred_intent["direct_ask"] = (
            "own the job through connect, follow-up, iterate, and check without another user turn"
        )
        contract.inferred_intent["recommended_cohesive_scope"] = (
            "the recovered job plus the self-handhold loop; no new product"
        )
        contract.inferred_intent["risks_if_partial"] = (
            "stopping after the first deliverable or asking the user to follow up repeats the miss"
        )

    if re.search(r"\b(delete|drop|destroy|overwrite)\b", instruction, re.I):
        contract.irreversible_or_external_actions.append("deletion")
        if _ambiguous_destructive(ctx):
            contract.unresolved_ambiguities.append("which backup location is meant")
            contract.unresolved_ambiguities.append(
                "ask the user before deleting, since readings diverge into materially different destructive work"
            )
            if contract.requested_action.startswith("change"):
                contract.requested_action = "unspecified"

    if re.search(r"\b(two|both|plausible|plausibly)\b", ctx, re.I):
        if not any("scope" in u or "which" in u for u in contract.unresolved_ambiguities):
            contract.unresolved_ambiguities.append(
                "whether both helper modules are in scope"
                if re.search(r"helper", ctx, re.I)
                else "which of the plausible referents is in scope"
            )
        if not any("choose-and-note" in a.lower() for a in contract.assumptions):
            contract.assumptions.append(
                "choose-and-note strategy: reversible interpretation may proceed with the choice recorded as an assumption"
            )

    # I2: preserve a stated motive clause; never replace objective with the blob.
    motive = STATED_MOTIVE.search(instruction)
    if motive:
        clause = " ".join(motive.group(0).split())
        if clause.lower() not in contract.objective.lower():
            contract.objective = (contract.objective + " — " + clause)[:240]
    # Preserve an already-stated deadline/CI motive that is part of the instruction.
    if re.search(r"\b(tonight|ci blocks|release)\b", instruction, re.I):
        for token in ("tonight", "ci", "release"):
            if token not in contract.objective.lower() and token in instruction.lower():
                contract.objective = (contract.objective + " " + token)[:240]

    return contract


def is_trivial(contract: ExecutionContract, decision: Route, executor: str = "fork") -> bool:
    """D3 only: single G1 / needs-context-expansion, local/self, no artifacts."""
    if decision.expect != "uplift":
        return False
    if contract.artifacts:
        return False
    if "G7" in decision.gaps:
        return False
    only_g1 = decision.gaps == ["G1"]
    only_ctx = only_g1 and all(r == "needs-context-expansion" for r in decision.reasons)
    if not (only_g1 or only_ctx):
        return False
    return executor in ("self", "local")


def normalize_target(target_model: str | None) -> str | None:
    if target_model is None:
        return None
    text = str(target_model).strip()
    return text or None


def _bullet_block(items: list[str], *, empty: str = NA_GENERIC) -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return empty
    return "\n".join(f"- {item}" for item in cleaned)


def _chassis_line(data: dict) -> str:
    blob = " ".join(
        [
            str(data.get("objective") or ""),
            str(data.get("requested_action") or ""),
            str(data.get("deliverable") or ""),
        ]
    ).lower()
    if any(token in blob for token in ("look up", "recommend", "closest", "find something")):
        return "research-analyst — lookup or comparison"
    if any(token in blob for token in ("why is", "broken", "repro", "debug")):
        return "regression-investigator — diagnose"
    if data.get("requested_action") in ("change", "build"):
        return "implementation-engineer — bounded change"
    return "commissioned-analyst — no roster row matched"


def render(contract: ExecutionContract, target_model: str | None = None) -> tuple[str, dict]:
    """Compile-spec skeleton. Model knobs stay in execution_hints.

    No target means no inference and no model-family notes. Unknown
    snapshots stay portable — no family knobs via prefix match.
    """
    target_model = normalize_target(target_model)
    data = contract.to_dict()
    inferred = data.get("inferred_intent") or {}
    objective_bits = [data["objective"], f"Requested action: {data['requested_action']}"]
    if data["deliverable"]:
        objective_bits.append(f"Deliverable: {data['deliverable']}")
    why = NA_WHY
    motive = STATED_MOTIVE.search(data["objective"] or "")
    if motive:
        why = " ".join(motive.group(0).split())

    recovered_items = list(data["relevant_context"])
    recovered_items.extend(data["artifacts"])
    recovered_items.extend(data["previous_failures"])
    for key in ("direct_ask", "adjacent_impact", "risks_if_partial"):
        value = inferred.get(key)
        if value:
            recovered_items.append(f"{key}: {value}")
    if inferred.get("session_signals"):
        recovered_items.append(
            "session_signals: " + ", ".join(inferred["session_signals"])
        )
    recovered_body = _bullet_block(recovered_items)
    if recovered_body != NA_GENERIC:
        recovered_body = "<recovered>\n" + recovered_body + "\n</recovered>"

    constraint_lines: list[str] = []
    for item in data["negations"]:
        constraint_lines.append(f"<negation>[negations] {item}</negation>")
    for item in data["authority_not_granted"]:
        constraint_lines.append(f"[authority_not_granted] {item}")
    for item in data["authority_granted"]:
        constraint_lines.append(f"[authority_granted] {item}")
    for item in data["hard_constraints"]:
        constraint_lines.append(f"[hard_constraints] {item}")
    for item in data["irreversible_or_external_actions"]:
        constraint_lines.append(f"[irreversible] {item}")

    assumptions = list(data["assumptions"])
    assumptions.extend(data["unresolved_ambiguities"])
    if data["unresolved_ambiguities"]:
        assumptions.append(
            "choose-and-note if reversible; ask only if readings diverge into different work"
        )
    assumptions.append("(non-normative; not user-stated requirements)")

    scope = inferred.get("recommended_cohesive_scope") or NA_GENERIC
    expansion = inferred.get("expansion") or "none"
    if expansion == "none":
        non_goals = (
            "what a reasonable executor might add that this job does not want"
        )
    else:
        non_goals = NA_GENERIC

    parts = [
        f"## Objective\n" + "\n".join(objective_bits),
        f"## Why\n{why}",
        f"## Recovered context\n{recovered_body}",
        f"## Constraints\n{_bullet_block(constraint_lines)}",
        f"## Scope\n{scope}",
        f"## Non-goals\n{non_goals}",
        f"## Evidence\n{_bullet_block(data['success_conditions'])}",
        f"## Output\n{_bullet_block(data['response_contract'])}",
        f"## Assumptions\n{_bullet_block(assumptions)}",
        f"## Chassis\n{_chassis_line(data)}",
    ]
    prompt = "\n\n".join(parts)
    checked = check_shape(prompt)
    if not checked.ok:
        raise ValueError("compiled spec failed shape-check: " + "; ".join(checked.reasons))
    hints: dict = {
        "context_policy": "fresh-executor",
    }
    if target_model:
        hints["target_model"] = target_model
        extra = SNAPSHOT_HINTS.get(target_model)
        if extra:
            hints.update(extra)
    return prompt, hints
