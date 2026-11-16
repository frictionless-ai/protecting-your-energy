"""Agent Skills evaluating-skills schema and workspace helpers.

Spec: https://agentskills.io/skill-creation/evaluating-skills

Authored cases live in ``skills/<name>/evals/evals.json``. Generated
iteration trees live under ``evals/workspaces/<name>/`` — the plugin-scale
equivalent of a sibling ``<skill>-workspace/`` so hosts that scan
``skills/`` do not treat a workspace as a skill.
"""

from __future__ import annotations

import json
import os
import math
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
CASE_ROOT = Path(os.environ.get("INTENT_RUNTIME_EVAL_CASES") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/skill-cases")
WORKSPACES = Path(os.environ.get("INTENT_RUNTIME_EVAL_WORKSPACE") or Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "protecting-your-energy/intent-runtime/evaluations")

REQUIRED_CASE = {"id", "prompt", "expected_output"}
OPTIONAL_CASE = {
    "files",
    "assertions",
    "slug",
    "session_context",
    "maps_to",
    "notes",
}
ALLOWED_CASE = REQUIRED_CASE | OPTIONAL_CASE
ARMS = ("with_skill", "without_skill", "old_skill")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillEvalError(ValueError):
    pass


def skill_dir(name: str) -> Path:
    return SKILLS / name


def evals_path(name: str) -> Path:
    return CASE_ROOT / name / "evals.json"


def workspace_root(name: str) -> Path:
    return WORKSPACES / name


def iteration_dir(name: str, iteration: int) -> Path:
    if iteration < 1:
        raise SkillEvalError("iteration must be >= 1")
    return workspace_root(name) / f"iteration-{iteration}"


def eval_dir(name: str, iteration: int, slug: str) -> Path:
    return iteration_dir(name, iteration) / f"eval-{slug}"


def arm_dir(name: str, iteration: int, slug: str, arm: str) -> Path:
    if arm not in ARMS:
        raise SkillEvalError(f"arm must be one of {ARMS}")
    return eval_dir(name, iteration, slug) / arm


def list_skill_names() -> list[str]:
    return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def load_evals(name: str) -> dict[str, Any]:
    path = evals_path(name)
    if not path.is_file():
        raise SkillEvalError(f"missing {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_payload(data, name)
    if problems:
        raise SkillEvalError("; ".join(problems))
    return data


def validate_payload(data: Any, expected_name: str | None = None) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"]
    if data.get("skill_name") in (None, ""):
        problems.append("skill_name is required")
    elif expected_name and data["skill_name"] != expected_name:
        problems.append(
            f"skill_name {data['skill_name']!r} != directory {expected_name!r}"
        )
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        problems.append("evals must be a non-empty list")
        return problems
    ids: set[int] = set()
    slugs: set[str] = set()
    for i, case in enumerate(evals):
        prefix = f"evals[{i}]"
        if not isinstance(case, dict):
            problems.append(f"{prefix} must be an object")
            continue
        extra = set(case) - ALLOWED_CASE
        if extra:
            problems.append(f"{prefix} unknown keys: {sorted(extra)}")
        missing = REQUIRED_CASE - set(case)
        if missing:
            problems.append(f"{prefix} missing {sorted(missing)}")
        cid = case.get("id")
        if not isinstance(cid, int) or isinstance(cid, bool) or cid < 1:
            problems.append(f"{prefix}.id must be an integer >= 1")
        elif cid in ids:
            problems.append(f"{prefix}.id {cid} is duplicated")
        else:
            ids.add(cid)
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            problems.append(f"{prefix}.prompt must be a non-empty string")
        expected = case.get("expected_output")
        if not isinstance(expected, str) or not expected.strip():
            problems.append(f"{prefix}.expected_output must be a non-empty string")
        files = case.get("files", [])
        if files is not None and (
            not isinstance(files, list) or any(not isinstance(f, str) for f in files)
        ):
            problems.append(f"{prefix}.files must be a list of strings")
        assertions = case.get("assertions", [])
        if assertions is not None:
            if not isinstance(assertions, list) or any(
                not isinstance(a, str) or not a.strip() for a in assertions
            ):
                problems.append(f"{prefix}.assertions must be a list of non-empty strings")
        slug = case.get("slug") or _default_slug(cid if isinstance(cid, int) else i + 1)
        if not SLUG_RE.match(slug):
            problems.append(f"{prefix}.slug {slug!r} must be kebab-case")
        elif slug in slugs:
            problems.append(f"{prefix}.slug {slug!r} is duplicated")
        else:
            slugs.add(slug)
        for key in ("session_context", "maps_to", "notes"):
            if key in case and not isinstance(case[key], str):
                problems.append(f"{prefix}.{key} must be a string")
    return problems


def case_slug(case: dict[str, Any]) -> str:
    return case.get("slug") or _default_slug(int(case["id"]))


def _default_slug(cid: int) -> str:
    return f"case-{cid}"


def init_iteration(name: str, iteration: int) -> Path:
    data = load_evals(name)
    root = iteration_dir(name, iteration)
    for case in data["evals"]:
        slug = case_slug(case)
        for arm in ("with_skill", "without_skill"):
            (arm_dir(name, iteration, slug, arm) / "outputs").mkdir(
                parents=True, exist_ok=True
            )
    return root


def write_timing(path: Path, total_tokens: int, duration_ms: int, **extra: Any) -> None:
    payload = {"total_tokens": total_tokens, "duration_ms": duration_ms, **extra}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_grading(path: Path, assertion_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not assertion_results:
        raise SkillEvalError("assertion_results must not be empty")
    for row in assertion_results:
        for key in ("text", "passed", "evidence"):
            if key not in row:
                raise SkillEvalError(f"assertion result missing {key}")
        if not isinstance(row["text"], str) or not row["text"].strip():
            raise SkillEvalError("assertion text must be a non-empty string")
        if not isinstance(row["passed"], bool):
            raise SkillEvalError("assertion passed must be a boolean")
        if not isinstance(row["evidence"], str) or not row["evidence"].strip():
            raise SkillEvalError("PASS/FAIL needs concrete evidence")
    passed = sum(1 for r in assertion_results if r["passed"])
    failed = len(assertion_results) - passed
    payload = {
        "assertion_results": assertion_results,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(assertion_results),
            "pass_rate": passed / len(assertion_results),
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _mean_std(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stddev": 0.0}
    mean = statistics.fmean(values)
    stddev = statistics.pstdev(values) if len(values) > 1 else 0.0
    if math.isnan(stddev):
        stddev = 0.0
    return {"mean": mean, "stddev": stddev}


def aggregate_iteration(name: str, iteration: int) -> dict[str, Any]:
    data = load_evals(name)
    root = iteration_dir(name, iteration)
    if not root.is_dir():
        raise SkillEvalError(f"missing {root}")
    by_arm: dict[str, dict[str, list[float]]] = {}
    per_eval: list[dict[str, Any]] = []
    for case in data["evals"]:
        slug = case_slug(case)
        case_row: dict[str, Any] = {"id": case["id"], "slug": slug, "arms": {}}
        for arm in ARMS:
            grading_path = arm_dir(name, iteration, slug, arm) / "grading.json"
            if not grading_path.is_file():
                continue
            grading = load_json(grading_path)
            summary = grading.get("summary") or {}
            timing_path = arm_dir(name, iteration, slug, arm) / "timing.json"
            tokens = 0
            duration_ms = 0
            if timing_path.is_file():
                timing = load_json(timing_path)
                tokens = int(timing.get("total_tokens") or 0)
                duration_ms = int(timing.get("duration_ms") or 0)
            pass_rate = float(summary.get("pass_rate") or 0.0)
            bucket = by_arm.setdefault(
                arm, {"pass_rate": [], "time_seconds": [], "tokens": []}
            )
            bucket["pass_rate"].append(pass_rate)
            bucket["time_seconds"].append(duration_ms / 1000.0)
            bucket["tokens"].append(float(tokens))
            case_row["arms"][arm] = {
                "pass_rate": pass_rate,
                "passed": summary.get("passed"),
                "failed": summary.get("failed"),
                "total": summary.get("total"),
                "tokens": tokens,
                "duration_ms": duration_ms,
            }
        per_eval.append(case_row)

    run_summary: dict[str, Any] = {}
    for arm, bucket in by_arm.items():
        run_summary[arm] = {
            "pass_rate": _mean_std(bucket["pass_rate"]),
            "time_seconds": _mean_std(bucket["time_seconds"]),
            "tokens": _mean_std(bucket["tokens"]),
        }
    if "with_skill" in run_summary and "without_skill" in run_summary:
        run_summary["delta"] = {
            "pass_rate": (
                run_summary["with_skill"]["pass_rate"]["mean"]
                - run_summary["without_skill"]["pass_rate"]["mean"]
            ),
            "time_seconds": (
                run_summary["with_skill"]["time_seconds"]["mean"]
                - run_summary["without_skill"]["time_seconds"]["mean"]
            ),
            "tokens": (
                run_summary["with_skill"]["tokens"]["mean"]
                - run_summary["without_skill"]["tokens"]["mean"]
            ),
        }
    elif "with_skill" in run_summary and "old_skill" in run_summary:
        run_summary["delta"] = {
            "pass_rate": (
                run_summary["with_skill"]["pass_rate"]["mean"]
                - run_summary["old_skill"]["pass_rate"]["mean"]
            ),
            "time_seconds": (
                run_summary["with_skill"]["time_seconds"]["mean"]
                - run_summary["old_skill"]["time_seconds"]["mean"]
            ),
            "tokens": (
                run_summary["with_skill"]["tokens"]["mean"]
                - run_summary["old_skill"]["tokens"]["mean"]
            ),
        }

    payload = {
        "skill_name": name,
        "iteration": iteration,
        "run_summary": run_summary,
        "evals": per_eval,
    }
    out = root / "benchmark.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def write_feedback(name: str, iteration: int, notes: dict[str, str]) -> Path:
    root = iteration_dir(name, iteration)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "feedback.json"
    existing: dict[str, str] = {}
    if path.is_file():
        existing = load_json(path)
    existing.update(notes)
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return path


def grade_from_needles(
    assertions: list[str],
    haystack: str,
    *,
    missing_needles: list[str],
    invented: list[str],
    extra_fails: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Mechanical grader for preview/harness arms. Live grading is semantic."""
    hay = haystack.lower()
    results: list[dict[str, Any]] = []
    extra_fails = extra_fails or []
    for text in assertions:
        lowered = text.lower()
        if any(n.lower() in lowered for n in invented):
            passed = False
            evidence = f"invented needle present in output: {invented}"
        elif any(n.lower() in lowered for n in missing_needles):
            passed = False
            evidence = f"required needle missing from output: {missing_needles}"
        elif any(fail.lower() in lowered for fail in extra_fails):
            passed = False
            evidence = "arm failed an extra check"
        else:
            # Assertion names the property; pass if no missing/invented on this arm.
            passed = not missing_needles and not invented
            if passed:
                evidence = "Needles present; no invented extras in this arm"
            else:
                evidence = (
                    f"missing={missing_needles or []} invented={invented or []}"
                )
        # If the assertion quotes a concrete token, require it in the haystack.
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", text)
        tokens = [a or b for a, b in quoted]
        if tokens and not all(tok.lower() in hay for tok in tokens):
            passed = False
            evidence = f"quoted token missing from output: {tokens}"
        results.append({"text": text, "passed": passed, "evidence": evidence})
    return results
