#!/usr/bin/env python3
"""Fresh-context activation eval for intent-runtime.

Each case in evals/activation/cases.jsonl is a prompt plus an expected
verdict. The runner starts a headless `claude -p` session with this
plugin loaded and looks for a real Skill invocation of intent-runtime
in the stream-json transcript or the telemetry store.

The user message is sent as-is. The probe does not name the skill —
naming it would measure instruction-following, not discovery, and
would make a naive string match always fire.

Usage:
    python3 scripts/eval_activation.py --dry-run
    python3 scripts/eval_activation.py --cases evals/activation/smoke.jsonl \\
        --timeout 60 --out docs/research/activation-eval-results.md

A mid-suite session failure is recorded as an error for that case and
does not stop the rest. Exit 0 always unless the cases file is missing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
EVAL_DATA = Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals")
DEFAULT_CASES = EVAL_DATA / "activation" / "cases.jsonl"
SKILL = "intent-runtime"


def load_cases(path: Path) -> list:
    cases = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def _iter_json_values(text: str):
    """Yield parsed JSON values from a blob that may be json, ndjson, or mixed."""
    text = text or ""
    try:
        yield json.loads(text)
        return
    except json.JSONDecodeError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _skill_from_tool_input(inp) -> str:
    if isinstance(inp, dict):
        for key in ("skill", "name", "skill_name", "skillName", "command"):
            val = inp.get(key)
            if isinstance(val, str) and val:
                return val
        args = inp.get("args") or inp.get("arguments")
        if isinstance(args, str) and args:
            return args.split()[0]
    if isinstance(inp, str):
        return inp.split()[0] if inp.strip() else ""
    return ""


def transcript_invoked_skill(obj, skill: str = SKILL) -> bool:
    """True when obj is (or contains) a Skill tool use of `skill`."""
    if obj is None:
        return False
    if isinstance(obj, list):
        return any(transcript_invoked_skill(x, skill) for x in obj)
    if not isinstance(obj, dict):
        return False

    name = obj.get("name") or obj.get("tool") or obj.get("tool_name")
    inp = (
        obj.get("input")
        or obj.get("tool_input")
        or obj.get("toolInput")
        or obj.get("tool_args")
    )
    if isinstance(name, str) and name.lower() in {"skill", "skillinvoke"}:
        target = _skill_from_tool_input(inp)
        if skill in target:
            return True

    event = str(obj.get("event") or obj.get("type") or "")
    if event in {"SkillInvoke", "skill_invoke"}:
        blob = json.dumps(
            {
                "input": inp,
                "tool_input": obj.get("tool_input"),
                "payload": obj.get("payload"),
            },
            default=str,
        )
        if skill in blob:
            return True

    return any(transcript_invoked_skill(v, skill) for v in obj.values())


def telemetry_invoked_skill(telemetry_dir: Path | None, skill: str = SKILL) -> bool:
    if telemetry_dir is None or not telemetry_dir.is_dir():
        return False
    for path in telemetry_dir.rglob("*.jsonl"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for obj in _iter_json_values(text):
            if not isinstance(obj, dict):
                continue
            event = str(obj.get("event") or "")
            tool = str(obj.get("tool_name") or "")
            if event == "SkillInvoke" or tool.lower() == "skill":
                if transcript_invoked_skill(obj, skill):
                    return True
                blob = json.dumps(
                    obj.get("tool_input") or obj.get("payload") or {},
                    default=str,
                )
                if skill in blob:
                    return True
    return False


def detect_activation(
    transcript: str, telemetry_dir: Path | None, skill: str = SKILL
) -> bool:
    """Activation is a Skill tool use or SkillInvoke record, not a mention."""
    for obj in _iter_json_values(transcript):
        if transcript_invoked_skill(obj, skill):
            return True
    return telemetry_invoked_skill(telemetry_dir, skill)


def user_blob(case: dict) -> str:
    prior = case.get("prior_turns") or []
    current = case["prompt"]
    if not prior:
        return current
    earlier = "\n\n".join(f"Earlier message: {turn}" for turn in prior)
    return f"{earlier}\n\nCurrent message: {current}"


def run_case(
    case: dict,
    plugin_root: Path,
    timeout: int,
    artifacts: Path | None,
    skill: str = SKILL,
) -> dict:
    prompt = user_blob(case)
    env = os.environ.copy()
    home = Path(tempfile.mkdtemp(prefix="mr-eval-"))
    env["MISSIONRUNTIME_HOME"] = str(home)
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--effort",
        "low",
        "--allowedTools",
        "Skill",
        "--disallowedTools",
        "Bash,Edit,Write,Read,Grep,Glob,Agent,Task",
        "--plugin-dir",
        str(plugin_root),
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=plugin_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if "Not logged in" in out or "authentication_failed" in out:
            return {
                "id": case["id"],
                "ok": False,
                "activated": False,
                "exit": proc.returncode,
                "error": "auth",
                "artifact": "",
            }
        activated = detect_activation(out, home, skill)
        if artifacts is not None:
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / f"{case['id']}.txt").write_text(out, encoding="utf-8")
        return {
            "id": case["id"],
            "ok": True,
            "activated": activated,
            "exit": proc.returncode,
            "error": "",
            "artifact": str(artifacts / f"{case['id']}.txt") if artifacts else "",
        }
    except FileNotFoundError:
        return {
            "id": case["id"],
            "ok": False,
            "activated": False,
            "exit": None,
            "error": "claude not on PATH",
            "artifact": "",
        }
    except subprocess.TimeoutExpired as exc:
        out = ""
        if exc.stdout:
            out += exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(
                "utf-8", "replace"
            )
        if exc.stderr:
            out += "\n" + (
                exc.stderr if isinstance(exc.stderr, str)
                else exc.stderr.decode("utf-8", "replace")
            )
        activated = detect_activation(out, home, skill)
        if artifacts is not None and out:
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / f"{case['id']}.txt").write_text(out, encoding="utf-8")
        return {
            "id": case["id"],
            "ok": False,
            "activated": activated,
            "exit": None,
            "error": "timeout",
            "artifact": str(artifacts / f"{case['id']}.txt") if artifacts and out else "",
        }
    except Exception as exc:  # noqa: BLE001 — per-case isolation
        return {
            "id": case["id"],
            "ok": False,
            "activated": False,
            "exit": None,
            "error": f"{type(exc).__name__}: {exc}",
            "artifact": "",
        }


def metrics(cases: list, results: list) -> dict:
    by_id = {r["id"]: r for r in results}
    tp = fp = tn = fn = errors = 0
    by_family = Counter()
    family_fn = Counter()
    family_fp = Counter()
    for case in cases:
        r = by_id.get(case["id"])
        if r is None or not r["ok"]:
            errors += 1
            continue
        expected = case["expected"]
        # Ambiguous cases are scored separately and do not enter P/R.
        if expected == "ambiguous":
            by_family[case["family"] + ":ambiguous"] += 1
            continue
        want = expected == "should_trigger"
        got = r["activated"]
        if want and got:
            tp += 1
        elif want and not got:
            fn += 1
            family_fn[case["family"]] += 1
        elif (not want) and got:
            fp += 1
            family_fp[case["family"]] += 1
        else:
            tn += 1
        by_family[case["family"]] += 1
    recall = tp / (tp + fn) if (tp + fn) else None
    precision = tp / (tp + fp) if (tp + fp) else None
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "errors": errors,
        "recall": recall,
        "precision": precision,
        "family_fn": dict(family_fn),
        "family_fp": dict(family_fp),
        "by_family": dict(by_family),
    }


def write_report(path: Path, cases: list, results: list, m: dict, note: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Activation eval results",
        "",
        note,
        "",
        f"Cases scored: {m['tp'] + m['fp'] + m['tn'] + m['fn']}. "
        f"Errors: {m['errors']}.",
        "",
        f"- Recall: {_fmt(m['recall'])} (fn={m['fn']})",
        f"- Precision: {_fmt(m['precision'])} (fp={m['fp']})",
        f"- True negatives: {m['tn']}",
        "",
        "## False negatives by family",
        "",
    ]
    if m["family_fn"]:
        for fam, n in sorted(m["family_fn"].items()):
            lines.append(f"- `{fam}`: {n}")
    else:
        lines.append("- none")
    lines += ["", "## False positives by family", ""]
    if m["family_fp"]:
        for fam, n in sorted(m["family_fp"].items()):
            lines.append(f"- `{fam}`: {n}")
    else:
        lines.append("- none")
    lines += ["", "## Per-case", "", "| id | family | expected | activated | error |",
              "|---|---|---|---|---|"]
    by_id = {r["id"]: r for r in results}
    for case in cases:
        r = by_id.get(case["id"], {})
        lines.append(
            f"| {case['id']} | {case['family']} | {case['expected']} | "
            f"{r.get('activated', '')} | {r.get('error', 'missing')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value):
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    p.add_argument(
        "--skill",
        help="Load skills/<skill>/evals/<split>_queries.json (official trigger format)",
    )
    p.add_argument(
        "--split",
        choices=("trigger", "train", "validation", "holdout"),
        default="validation",
        help="Which per-skill query file to use with --skill",
    )
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", type=Path)
    p.add_argument("--plugin-root", type=Path, default=REPO)
    p.add_argument(
        "--artifacts",
        type=Path,
        default=EVAL_DATA / "activation" / "artifacts",
    )
    args = p.parse_args(argv)
    skill = args.skill or SKILL

    if args.skill:
        from support.harness.skill_descriptions import (
            load_queries,
            queries_path,
            to_activation_cases,
        )

        qpath = queries_path(args.skill, args.split)
        if not qpath.is_file():
            raise SystemExit(f"missing query file: {qpath}")
        cases = to_activation_cases(load_queries(qpath), args.skill)
    else:
        if not args.cases.is_file():
            raise SystemExit(f"missing cases file: {args.cases}")
        cases = load_cases(args.cases)
    if args.limit:
        cases = cases[: args.limit]

    if args.dry_run:
        print(json.dumps({"n": len(cases), "ids": [c["id"] for c in cases]}, indent=2))
        return 0

    results = []
    for case in cases:
        results.append(
            run_case(case, args.plugin_root, args.timeout, args.artifacts, skill)
        )
        print(json.dumps(results[-1]), flush=True)

    m = metrics(cases, results)
    print(json.dumps({k: v for k, v in m.items() if k != "by_family"}, indent=2))
    note = (
        "Fresh-context `claude -p` runs. The user message is sent as-is "
        "(prior turns planted as earlier messages). Activation = a Skill "
        "tool use of `intent-runtime` in the stream-json transcript, or a "
        "`SkillInvoke` telemetry record — not a mention of the skill name. "
        "The first smoke run treated any occurrence of the string as a hit; "
        "that detector is retired because the listing and any named probe "
        "always contain it."
    )
    if any(r.get("error") == "claude not on PATH" for r in results):
        note += " `claude` was not on PATH; cases are recorded as errors."
    if args.out:
        write_report(args.out, cases, results, m, note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
