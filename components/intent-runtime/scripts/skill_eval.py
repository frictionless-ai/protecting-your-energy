#!/usr/bin/env python3
"""Eval-driven skill loop from https://agentskills.io/skill-creation/evaluating-skills

Commands:
  validate              check every skills/*/evals/evals.json
  init                  create iteration-N/{eval-slug}/{with,without}_skill/outputs
  grade                 write grading.json (+ optional timing.json) for one arm
  aggregate             write iteration-level benchmark.json
  feedback              merge human notes into feedback.json
  preview               harness A/B for cases with maps_to (not a live pass)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from support.harness.skill_evals import (  # noqa: E402
    ARMS,
    SkillEvalError,
    aggregate_iteration,
    arm_dir,
    case_slug,
    init_iteration,
    list_skill_names,
    load_evals,
    validate_payload,
    write_feedback,
    write_grading,
    write_timing,
    evals_path,
)


def _cmd_validate(_: argparse.Namespace) -> int:
    failed = 0
    for name in list_skill_names():
        path = evals_path(name)
        if not path.is_file():
            print(f"{name}: missing {path}")
            failed += 1
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        problems = validate_payload(data, name)
        if problems:
            failed += 1
            print(f"{name}:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"{name}: {len(data['evals'])} evals ok")
    return 1 if failed else 0


def _cmd_init(args: argparse.Namespace) -> int:
    root = init_iteration(args.skill, args.iteration)
    print(root)
    return 0


def _cmd_grade(args: argparse.Namespace) -> int:
    data = load_evals(args.skill)
    case = next((c for c in data["evals"] if c["id"] == args.eval_id), None)
    if case is None:
        print(f"no eval id {args.eval_id}", file=sys.stderr)
        return 2
    slug = case_slug(case)
    dest = arm_dir(args.skill, args.iteration, slug, args.arm)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "outputs").mkdir(exist_ok=True)
    raw = sys.stdin.read() if args.results == "-" else Path(args.results).read_text()
    payload = json.loads(raw)
    results = payload.get("assertion_results") or payload.get("results")
    if not isinstance(results, list):
        print("results must include assertion_results", file=sys.stderr)
        return 2
    write_grading(dest / "grading.json", results)
    timing = payload.get("timing")
    if timing:
        write_timing(
            dest / "timing.json",
            int(timing.get("total_tokens") or 0),
            int(timing.get("duration_ms") or 0),
            **{k: v for k, v in timing.items() if k not in {"total_tokens", "duration_ms"}},
        )
    print(dest / "grading.json")
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    payload = aggregate_iteration(args.skill, args.iteration)
    print(json.dumps(payload["run_summary"], indent=2))
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    key = args.eval_slug
    if not key.startswith("eval-"):
        key = f"eval-{key}"
    path = write_feedback(args.skill, args.iteration, {key: args.text})
    print(path)
    return 0


def _session_cases() -> dict[str, dict]:
    path = Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "cases.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    return {c["id"]: c for c in blob["cases"]}


def _cmd_preview(args: argparse.Namespace) -> int:
    """Harness A/B for mapped cases. Source is harness-preview, not live-skill."""
    from support.harness.inspector import review_case

    data = load_evals(args.skill)
    fixtures = _session_cases()
    init_iteration(args.skill, args.iteration)
    ran = 0
    for case in data["evals"]:
        maps_to = case.get("maps_to")
        if not maps_to or maps_to not in fixtures:
            continue
        fixture = fixtures[maps_to]
        review = review_case(fixture)
        slug = case_slug(case)
        assertions = case.get("assertions") or [
            "Required session constraints survive",
            "No invented extras",
        ]
        for arm, score in (
            ("with_skill", review.compiled),
            ("without_skill", review.naive),
        ):
            dest = arm_dir(args.skill, args.iteration, slug, arm)
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "outputs").mkdir(exist_ok=True)
            results = []
            for text in assertions:
                missing = score.missing
                invented = score.invented
                passed = not missing and not invented
                evidence = (
                    f"harness-preview route={score.route} "
                    f"missing={missing or []} invented={invented or []} "
                    f"survived={score.survived or []}"
                )
                results.append({"text": text, "passed": passed, "evidence": evidence})
            write_grading(dest / "grading.json", results)
            write_timing(
                dest / "timing.json",
                total_tokens=0,
                duration_ms=0,
                source="harness-preview",
            )
            (dest / "outputs" / "preview.json").write_text(
                json.dumps(
                    {
                        "source": "harness-preview",
                        "case_id": maps_to,
                        "route": score.route,
                        "score": score.score,
                    },
                    indent=2,
                )
                + "\n"
            )
        ran += 1
    if ran == 0:
        print("no mapped cases to preview", file=sys.stderr)
        return 2
    payload = aggregate_iteration(args.skill, args.iteration)
    print(f"previewed {ran} evals")
    print(json.dumps(payload["run_summary"], indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("init")
    p.add_argument("--skill", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.set_defaults(func=_cmd_init)

    p = sub.add_parser("grade")
    p.add_argument("--skill", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.add_argument("--eval-id", type=int, required=True)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--results", default="-", help="JSON file or - for stdin")
    p.set_defaults(func=_cmd_grade)

    p = sub.add_parser("aggregate")
    p.add_argument("--skill", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.set_defaults(func=_cmd_aggregate)

    p = sub.add_parser("feedback")
    p.add_argument("--skill", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.add_argument("--eval-slug", required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=_cmd_feedback)

    p = sub.add_parser("preview")
    p.add_argument("--skill", required=True)
    p.add_argument("--iteration", type=int, default=1)
    p.set_defaults(func=_cmd_preview)

    args = parser.parse_args()
    try:
        return args.func(args)
    except SkillEvalError as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
