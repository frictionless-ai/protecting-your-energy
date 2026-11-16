#!/usr/bin/env python3
"""Live compile / delegation checks for intent-runtime.

Scores whether semantic constraints survive into the compiled spec
(the artifact that would be the Task prompt) and whether presentation
directives stay out of Constraints.

Usage:
    python3 scripts/eval_delegation.py --dry-run
    python3 scripts/eval_delegation.py --out docs/research/delegation-eval-results.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAIRS = REPO / "evals" / "quality" / "pairs"
ROSTER = {
    "repo-cartographer",
    "research-analyst",
    "commissioned-analyst",
    "implementation-engineer",
    "test-engineer",
    "security-reviewer",
    "code-quality-reviewer",
    "regression-investigator",
    "docs-writer",
    "adversarial-critic",
}

# Three corpus-derived tasks required by the plan: environment recovery,
# fragment amendment, and style split.
DEFAULT_IDS = ("q-001", "q-002", "q-003")

COMPILE_PREFIX = (
    "Using the intent-runtime compile procedure, compile a self-contained "
    "execution spec for the user conversation below. Print only:\n\n"
    "## SPEC\n"
    "(the nine-slot spec that would be sent as the Task prompt)\n\n"
    "## STYLE\n"
    "(presentation preferences held at the parent, or the word none)\n\n"
    "Do not dispatch Task. Do not solve the user's task. Do not invent "
    "requirements. Do not put tone, length, or formatting into Constraints.\n\n"
    "CONVERSATION:\n"
)


def load_pairs(ids: tuple[str, ...] | None = None) -> list:
    pairs = []
    for path in sorted(PAIRS.glob("*.json")):
        pair = json.loads(path.read_text(encoding="utf-8"))
        if ids and pair.get("id") not in ids:
            continue
        pairs.append(pair)
    return pairs


def conversation(pair: dict) -> str:
    prior = pair.get("prior_turns") or []
    body = "\n".join(f"Earlier message: {t}" for t in prior)
    current = f"Current message: {pair['prompt']}"
    return f"{body}\n\n{current}".strip()


def split_spec_style(text: str) -> tuple[str, str]:
    low = text
    spec_m = re.search(r"##\s*SPEC\b(.*?)(?:##\s*STYLE\b|$)", low, re.S | re.I)
    style_m = re.search(r"##\s*STYLE\b(.*)$", low, re.S | re.I)
    spec = spec_m.group(1) if spec_m else text
    style = style_m.group(1) if style_m else ""
    return spec, style


def constraints_block(spec: str) -> str:
    m = re.search(
        r"##\s*Constraints\b(.*?)(?:##\s|\Z)", spec, re.S | re.I
    )
    return m.group(1) if m else spec


def score_pair(text: str, pair: dict) -> dict:
    spec, style = split_spec_style(text)
    constraints = constraints_block(spec)
    survived = [c for c in pair.get("must_survive", []) if c.lower() in spec.lower()]
    missing = [c for c in pair.get("must_survive", []) if c.lower() not in spec.lower()]
    invented = [c for c in pair.get("must_not_invent", []) if c.lower() in spec.lower()]
    leaked = [
        p for p in pair.get("presentation", []) if p.lower() in constraints.lower()
    ]
    style_held = [
        p for p in pair.get("presentation", []) if p.lower() in style.lower()
    ]
    chassis = sorted(name for name in ROSTER if name in spec)
    return {
        "survived": survived,
        "missing": missing,
        "invented_hits": invented,
        "presentation_leaked": leaked,
        "style_held": style_held,
        "chassis": chassis,
        # Chassis is reported; a variant template without a roster name
        # still passes if semantic needles survived and style did not leak.
        "pass": not missing and not invented and not leaked,
    }


def run_once(prompt: str, cwd: Path, timeout: int, artifacts: Path, pair_id: str) -> dict:
    env = os.environ.copy()
    env["MISSIONRUNTIME_HOME"] = str(Path(tempfile.mkdtemp(prefix="mr-del-")))
    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--output-format",
                "json",
                "--effort",
                "low",
                "--allowedTools",
                "Skill,Read",
                "--disallowedTools",
                "Bash,Edit,Write,Grep,Glob,Agent,Task",
                "--plugin-dir",
                str(cwd),
            ],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / f"{pair_id}.txt").write_text(out, encoding="utf-8")
        return {"ok": True, "text": out, "error": "", "artifact": str(artifacts / f"{pair_id}.txt")}
    except FileNotFoundError:
        return {"ok": False, "text": "", "error": "claude not on PATH", "artifact": ""}
    except subprocess.TimeoutExpired as exc:
        out = ""
        if exc.stdout:
            out += exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(
                "utf-8", "replace"
            )
        return {"ok": False, "text": out, "error": "timeout", "artifact": ""}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": "", "error": f"{type(exc).__name__}: {exc}", "artifact": ""}


def write_report(path: Path, rows: list, note: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Delegation / compile-spec live checks",
        "",
        note,
        "",
        "| id | pass | missing | leaked | chassis | error |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row.get('pass', '')} | "
            f"{', '.join(row.get('missing', [])) or '—'} | "
            f"{', '.join(row.get('presentation_leaked', [])) or '—'} | "
            f"{', '.join(row.get('chassis', [])) or '—'} | "
            f"{row.get('error', '')} |"
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--out", type=Path)
    p.add_argument("--plugin-root", type=Path, default=REPO)
    p.add_argument(
        "--artifacts",
        type=Path,
        default=REPO / "evals" / "delegation" / "artifacts",
    )
    p.add_argument("--ids", nargs="*", default=list(DEFAULT_IDS))
    args = p.parse_args(argv)

    pairs = load_pairs(tuple(args.ids) if args.ids else None)
    if args.dry_run:
        print(json.dumps({"n": len(pairs), "ids": [x["id"] for x in pairs]}, indent=2))
        return 0

    rows = []
    for pair in pairs:
        live = run_once(
            COMPILE_PREFIX + conversation(pair),
            args.plugin_root,
            args.timeout,
            args.artifacts,
            pair["id"],
        )
        scored = score_pair(live.get("text", ""), pair)
        row = {
            "id": pair["id"],
            "error": live.get("error", ""),
            "artifact": live.get("artifact", ""),
            **scored,
        }
        if live.get("error"):
            row["pass"] = False
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "survived"}, default=str), flush=True)

    note = (
        "Live compile checks. The printed SPEC is the Task-prompt stand-in "
        "(Task itself is disallowed so the run cannot hide inside an "
        "executor). Semantic needles must appear in SPEC; presentation "
        "phrases must not appear under Constraints. Chassis must be a "
        "roster name. Artifacts: `evals/delegation/artifacts/`."
    )
    if args.out:
        write_report(args.out, rows, note)
    print(json.dumps({"rows": rows}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
