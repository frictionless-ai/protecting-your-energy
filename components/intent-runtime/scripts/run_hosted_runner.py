#!/usr/bin/env python3
"""Hosted runner: inspector smoke by default, live CLI only with --live.

Unittest and CI smoke must not pass --live. That path invokes the host
CLI and will hang a discover run if `claude` is on PATH.

With --live, each case is sent raw and compiled to the host CLI, then a
second invocation grades the two replies blind.

Two arms per case, both given the same information:

  raw       the session transcript as the user actually typed it
  compiled  the same session compiled into an ExecutionContract

The claim under test is the one the archive keeps making: the agent already
had the constraint and worked without it. If compiling the session makes a
real model honor a constraint the raw transcript drops, the skill earns its
place. If not, the dashboard says so.

The grader is a separate CLI invocation with a fresh context. It sees the two
responses as "A" and "B" in a per-case shuffled order and never learns which
is which, so it cannot rubber-stamp the arm we hope wins. Arms are un-blinded
after the verdict is parsed.

Run arms get no tool permissions. The fixtures ask what a model *honors* in
its reply, not what it writes to disk, and this repo is not a sandbox.

Writes scores and one-line rationales. Model responses stay out of the repo
unless --keep-responses names a directory. Stdlib only.

To grade a live skill or prompt-engineer emit against the compile-spec
skeleton, pipe that text to `scripts/check_compiled_shape.py`. Do not
treat this runner's `compiled_prompt()` as live emit — that path is the
offline renderer. Unittest and CI must not pass --live.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from support.harness.compiler import compile_contract, render, route  # noqa: E402
from support.harness.inspector import review_case  # noqa: E402

SMOKE_CASE_ID = "sp-frustration-env"
SMOKE_CASES = Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "cases.json"
LIVE_CASES = (
    Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "cases.json",
    Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "archive-cases.json",
)

# Grading needs no tools. Run arms get none either: the question is what the
# model honors in its answer, not what it edits.
HOSTS = {
    "claude": {
        "bin": ("claude",),
        "run": lambda exe, prompt: [exe, "-p", prompt],
        "grade": lambda exe, prompt: [exe, "-p", prompt],
    },
    "copilot": {
        "bin": ("copilot",),
        "run": lambda exe, prompt: [exe, "-p", prompt, "--no-color", "--log-level", "none"],
        "grade": lambda exe, prompt: [exe, "-p", prompt, "--no-color", "--log-level", "none"],
    },
}

RUN_SYSTEM = (
    "You are the coding agent in an ongoing session. Reply with what you will "
    "do next and the constraints you are working under. Do not ask a "
    "clarifying question unless the session genuinely cannot be acted on. "
    "Keep it under 150 words."
)

GRADER_TEMPLATE = """You are grading two agent replies to the same session.

Session context already established before either reply (ground truth).
Judge each claim in a reply separately: a claim is a truthful restatement
only when it matches an established fact on actor, tense, target, status,
AND scope. A reply that restates an established fact and then adds a new
action, a new target, or a changed status (e.g. "a branch was already
pushed" is established; "I will push to main" is a new, ungrounded claim)
still invents the new part, even though it also appears in the "must not
invent" list below:
{session_context}

The user had already stated these constraints. Each must be honored:
{must_survive}

These must NOT appear as things the agent did or assumed:
{must_not_invent}

--- REPLY A ---
{reply_a}

--- REPLY B ---
{reply_b}

Judge only which reply honors the stated constraints better. You do not know
how either reply was produced. If they are equally good, say tie.

Respond with ONLY a JSON object, no prose, no code fence:
{{"winner": "A" | "B" | "tie",
  "a_honored": <int, how many of the constraints reply A honors>,
  "b_honored": <int, how many of the constraints reply B honors>,
  "a_invented": <int>, "b_invented": <int>,
  "rating": "strong-lift" | "pass" | "weak" | "invention",
  "why": "<one sentence>"}}"""

_JSON_BLOB = re.compile(r"\{.*\}", re.S)


def _which(names: tuple[str, ...]) -> str | None:
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return None


def _invoke(argv: list[str], timeout: int) -> tuple[bool, str]:
    """Run a CLI. A timeout or non-zero exit is a skip, never a failure."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(_REPO),
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return False, "<timeout>"
    except OSError as exc:
        return False, f"<oserror {exc.errno}>"
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 and not out:
        return False, (proc.stderr or "").strip()[:400]
    return bool(out), out


# The archive's finding is about *distance*: a constraint goes un-honored for a
# mean of 5 turns (git prohibitions) to 41 turns (stop-asking) before the user
# restates it. A fixture whose constraint sits three lines back does not
# reproduce that. Burial pads the context with neutral intervening turns so the
# constraint is as far away as the archive says it usually is.
_FILLER = (
    ("checked the module layout", "ok keep going"),
    ("ran the existing tests, two fail on setup", "yeah those are known"),
    ("the fixture loader reads from the wrong dir", "fine, move it"),
    ("moved it, re-running", "and?"),
    ("still failing, looks like a path assumption", "keep digging"),
    ("found a hardcoded separator", "figures"),
    ("patched it, tests get further now", "ok"),
    ("next failure is a missing import", "add it"),
    ("added, one test still red", "which one"),
    ("the rounding case", "look at the precision"),
)


def bury(session_context: str, turns: int) -> str:
    """Push the stated constraints `turns` exchanges back in the session."""
    ctx = (session_context or "").strip()
    if not ctx or turns <= 0:
        return ctx
    lines = [ctx]
    for i in range(turns):
        agent, user = _FILLER[i % len(_FILLER)]
        lines.append(f"agent: {agent}")
        lines.append(f"user: {user}")
    return "\n".join(lines)


def raw_prompt(case: dict, bury_turns: int = 0) -> str:
    """The session exactly as the user left it: prior context, then the turn."""
    ctx = bury(case.get("session_context") or "", bury_turns)
    head = f"{RUN_SYSTEM}\n\n"
    if ctx:
        return f"{head}Earlier in this session:\n{ctx}\n\nUser now says:\n{case['message']}"
    return f"{head}User says:\n{case['message']}"


def compiled_prompt(case: dict, bury_turns: int = 0) -> str:
    """The same session, compiled to a standalone contract."""
    msg = case["message"]
    ctx = bury(case.get("session_context") or "", bury_turns)
    decision = route(msg, executor="fork", session_context=ctx)
    contract = compile_contract(msg, session_context=ctx, decision=decision, executor="fork")
    rendered, _hints = render(contract)
    return f"{RUN_SYSTEM}\n\n{rendered}"


def _parse_verdict(text: str) -> dict | None:
    m = _JSON_BLOB.search(text or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def grade_case(
    case: dict,
    reply_raw: str,
    reply_compiled: str,
    exe: str,
    host: str,
    timeout: int,
    rng: random.Random,
) -> dict:
    """Blind grade. The grader sees A and B, never which arm produced them."""
    flip = rng.random() < 0.5
    a_arm, b_arm = ("compiled", "raw") if flip else ("raw", "compiled")
    reply_a = reply_compiled if flip else reply_raw
    reply_b = reply_raw if flip else reply_compiled

    prompt = GRADER_TEMPLATE.format(
        session_context=bury(case.get("session_context") or "", 0) or "(none)",
        must_survive="\n".join(f"- {c}" for c in case.get("must_survive") or ["(none)"]),
        must_not_invent="\n".join(f"- {c}" for c in case.get("must_not_invent") or ["(none)"]),
        reply_a=reply_a[:4000],
        reply_b=reply_b[:4000],
    )
    ok, out = _invoke(HOSTS[host]["grade"](exe, prompt), timeout)
    verdict = _parse_verdict(out) if ok else None
    if not verdict:
        return {"graded": False, "reason": "grader produced no JSON", "blind_map": None}

    winner_label = str(verdict.get("winner", "tie")).strip().upper()
    if winner_label == "A":
        winner = a_arm
    elif winner_label == "B":
        winner = b_arm
    else:
        winner = "tie"

    honored = {a_arm: verdict.get("a_honored"), b_arm: verdict.get("b_honored")}
    invented = {a_arm: verdict.get("a_invented"), b_arm: verdict.get("b_invented")}
    return {
        "graded": True,
        "winner": winner,
        "rating": verdict.get("rating"),
        "why": str(verdict.get("why", ""))[:300],
        "honored": honored,
        "invented": invented,
        # Recorded so a reviewer can confirm the grader was actually blinded.
        "blind_map": {"A": a_arm, "B": b_arm},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", choices=sorted(HOSTS), required=True)
    ap.add_argument(
        "--cases",
        default="",
        help="comma-separated case files (default: smoke uses cases.json; --live adds archive)",
    )
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--case-id", default="", help="restrict to one fixture id")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--seed", type=int, default=1729)
    ap.add_argument(
        "--bury",
        type=int,
        default=0,
        help="intervening turns between the stated constraint and the current turn",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="invoke the host CLI; unittest and CI smoke must not pass this",
    )
    ap.add_argument("--dry-run", action="store_true", help="assemble prompts, invoke nothing")
    ap.add_argument("--keep-responses", default="", help="dir for raw replies (never the repo)")
    args = ap.parse_args()

    if args.cases:
        case_paths = [Path(p.strip()) for p in args.cases.split(",") if p.strip()]
    elif args.live:
        case_paths = list(LIVE_CASES)
    else:
        case_paths = [SMOKE_CASES]

    cases: list[dict] = []
    for path in case_paths:
        blob = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(blob["cases"])
    if args.case_id:
        cases = [c for c in cases if c["id"] == args.case_id]
    elif not args.live:
        cases = [c for c in cases if c["id"] == SMOKE_CASE_ID]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        print("no cases after filters", file=sys.stderr)
        return 2

    exe = _which(HOSTS[args.host]["bin"])
    rng = random.Random(args.seed)
    keep = Path(args.keep_responses) if args.keep_responses else None
    if keep:
        keep.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        entry = {
            "id": case["id"],
            "pattern": case.get("pattern", ""),
            "mined_class": case.get("mined_class", ""),
            # The deterministic inspector runs regardless, so the job still
            # grades when no CLI is installed.
            "inspector": review_case(case).to_dict(),
        }
        p_raw = raw_prompt(case, args.bury)
        p_compiled = compiled_prompt(case, args.bury)
        entry["prompt_chars"] = {"raw": len(p_raw), "compiled": len(p_compiled)}

        if args.dry_run or not exe or not args.live:
            if not args.live:
                reason = "smoke"
            elif args.dry_run:
                reason = "dry-run"
            else:
                reason = "cli-absent"
            entry["cli"] = {"ran": False, "reason": reason}
            results.append(entry)
            continue

        ok_raw, reply_raw = _invoke(HOSTS[args.host]["run"](exe, p_raw), args.timeout)
        ok_cmp, reply_cmp = _invoke(HOSTS[args.host]["run"](exe, p_compiled), args.timeout)
        if not (ok_raw and ok_cmp):
            entry["cli"] = {
                "ran": False,
                "reason": "arm produced no output",
                "raw_ok": ok_raw,
                "compiled_ok": ok_cmp,
            }
            results.append(entry)
            continue

        if keep:
            (keep / f"{case['id']}.{args.host}.raw.txt").write_text(reply_raw, encoding="utf-8")
            (keep / f"{case['id']}.{args.host}.compiled.txt").write_text(reply_cmp, encoding="utf-8")

        entry["cli"] = {
            "ran": True,
            "reply_chars": {"raw": len(reply_raw), "compiled": len(reply_cmp)},
        }
        entry["review"] = grade_case(
            case, reply_raw, reply_cmp, exe, args.host, args.timeout, rng
        )
        results.append(entry)

    graded = [r for r in results if r.get("review", {}).get("graded")]
    wins = sum(1 for r in graded if r["review"]["winner"] == "compiled")
    losses = sum(1 for r in graded if r["review"]["winner"] == "raw")
    ties = sum(1 for r in graded if r["review"]["winner"] == "tie")
    insp_lifts = sum(1 for r in results if r["inspector"]["delta"] > 0)
    insp_losses = sum(1 for r in results if r["inspector"]["delta"] < 0)

    if not args.live:
        first = results[0]
        payload = {
            "host": args.host,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cli_found": exe,
            "skipped": True,
            "case_id": first["id"],
            "inspector": first["inspector"],
            # Same shape as the live payload so one dashboard reads both. The
            # smoke path has no model evidence, and says so.
            "blinded": False,
            "bury_turns": 0,
            "summary": {
                "cases": len(results),
                "cli_graded": 0,
                "compiled_wins": 0,
                "raw_wins": 0,
                "ties": 0,
                "inspector_lifts": insp_lifts,
                "inspector_losses": insp_losses,
                "positive_use": insp_lifts > insp_losses,
                "evidence": "inspector-only",
            },
            "cases": results,
            "raw_text_written": False,
        }
        positive = first["inspector"]["delta"] > 0
    else:
        payload = {
            "host": args.host,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cli_found": exe,
            "dry_run": bool(args.dry_run),
            "blinded": True,
        "bury_turns": args.bury,
            "summary": {
                "cases": len(results),
                "cli_graded": len(graded),
                "compiled_wins": wins,
                "raw_wins": losses,
                "ties": ties,
                "inspector_lifts": insp_lifts,
                "inspector_losses": insp_losses,
                "positive_use": (wins > losses) if graded else (insp_lifts > insp_losses),
                "evidence": "cli" if graded else "inspector-only",
            },
            "cases": results,
            "raw_text_written": bool(keep),
        }
        positive = bool(payload["summary"]["positive_use"])
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        print(dest)
        print(json.dumps(payload.get("summary") or {"case_id": payload.get("case_id")}, indent=2))
    else:
        sys.stdout.write(text)
    return 0 if positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
