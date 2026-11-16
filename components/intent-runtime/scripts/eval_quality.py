#!/usr/bin/env python3
"""Quality A/B eval: baseline vs intent-runtime path.

Each pair under evals/quality/pairs/ is a corpus-derived prompt with
must-survive constraints. Live mode runs two fresh `claude -p` sessions
(A = ask the model not to use plugin skills; B = normal, plugin present)
and scores constraint survival plus a verbosity heuristic.

Usage:
    python3 scripts/eval_quality.py --dry-run
    python3 scripts/eval_quality.py --out docs/research/quality-eval-results.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAIRS = REPO / "evals" / "quality" / "pairs"


def load_pairs() -> list:
    pairs = []
    for path in sorted(PAIRS.glob("*.json")):
        pairs.append(json.loads(path.read_text(encoding="utf-8")))
    return pairs


def score_text(text: str, pair: dict) -> dict:
    low = text.lower()
    survived = [c for c in pair.get("must_survive", []) if c.lower() in low]
    missing = [c for c in pair.get("must_survive", []) if c.lower() not in low]
    invented = [c for c in pair.get("must_not_invent", []) if c.lower() in low]
    return {
        "survived": survived,
        "missing": missing,
        "invented_hits": invented,
        "n_chars": len(text),
        "n_words": len(text.split()),
    }


def run_once(
    prompt: str,
    cwd: Path,
    timeout: int,
    extra_prefix: str,
    artifacts: Path | None = None,
    label: str = "",
) -> dict:
    env = os.environ.copy()
    env["MISSIONRUNTIME_HOME"] = str(Path(tempfile.mkdtemp(prefix="mr-qeval-")))
    full = extra_prefix + prompt
    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                full,
                "--output-format",
                "json",
                "--effort",
                "low",
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
        if artifacts is not None and label:
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / f"{label}.txt").write_text(out, encoding="utf-8")
        return {"ok": True, "text": out, "error": ""}
    except FileNotFoundError:
        return {"ok": False, "text": "", "error": "claude not on PATH"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": "", "error": f"{type(exc).__name__}: {exc}"}


def static_spec_check() -> list:
    """The compile-spec worked examples are the offline quality net."""
    spec = (
        REPO / "skills" / "intent-runtime" / "references" / "compile-spec.md"
    ).read_text(encoding="utf-8")
    checks = [
        ("fedora-winmerge", ["Fedora", "KDE", "WinMerge"]),
        ("yeah-fedora", ["Fedora", "Do not re-ask"]),
        ("less-writing", ["file:line", "terse"]),
        ("whats-this-mean", ["unrecoverable", "question packet"]),
        ("sorting-debug", ["bitrate", "regression-investigator"]),
    ]
    rows = []
    for name, needles in checks:
        missing = [n for n in needles if n not in spec]
        rows.append({"example": name, "missing": missing, "pass": not missing})
    return rows


def write_report(path: Path, pairs: list, live: list, static_rows: list, note: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Quality eval results",
        "",
        note,
        "",
        "## Static compile-spec checks",
        "",
        "| example | pass | missing |",
        "|---|---|---|",
    ]
    for row in static_rows:
        lines.append(
            f"| {row['example']} | {row['pass']} | "
            f"{', '.join(row['missing']) or '—'} |"
        )
    lines += ["", "## Pairs", "", f"{len(pairs)} pairs under `evals/quality/pairs/`.", ""]
    if live:
        lines += [
            "## Live A/B",
            "",
            "| id | A words | B words | A missing | B missing | error |",
            "|---|---:|---:|---|---|---|",
        ]
        for row in live:
            lines.append(
                f"| {row['id']} | {row.get('a_words', '')} | "
                f"{row.get('b_words', '')} | "
                f"{', '.join(row.get('a_missing', [])) or '—'} | "
                f"{', '.join(row.get('b_missing', [])) or '—'} | "
                f"{row.get('error', '')} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--live", action="store_true")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--ids", nargs="*")
    p.add_argument("--out", type=Path)
    p.add_argument("--plugin-root", type=Path, default=REPO)
    p.add_argument(
        "--artifacts",
        type=Path,
        default=REPO / "evals" / "quality" / "artifacts",
    )
    args = p.parse_args(argv)

    pairs = load_pairs()
    if args.ids:
        pairs = [x for x in pairs if x["id"] in args.ids]
    if args.limit:
        pairs = pairs[: args.limit]
    if args.dry_run:
        print(json.dumps({"n": len(pairs), "ids": [x["id"] for x in pairs]}, indent=2))
        return 0

    static_rows = static_spec_check()
    live = []
    if args.live:
        for pair in pairs:
            planted = ""
            if pair.get("prior_turns"):
                planted = (
                    "Earlier in this conversation the user said:\n"
                    + "\n".join(f"- {t}" for t in pair["prior_turns"])
                    + "\n\nNow the user says:\n"
                )
            a_prefix = (
                "Do not invoke any project skills. Answer the user message "
                "as a generic assistant.\n\n"
            )
            a = run_once(
                planted + pair["prompt"],
                args.plugin_root,
                args.timeout,
                a_prefix,
                args.artifacts,
                f"{pair['id']}-a",
            )
            b = run_once(
                planted + pair["prompt"],
                args.plugin_root,
                args.timeout,
                "",
                args.artifacts,
                f"{pair['id']}-b",
            )
            sa = score_text(a.get("text", ""), pair)
            sb = score_text(b.get("text", ""), pair)
            live.append({
                "id": pair["id"],
                "a_words": sa["n_words"],
                "b_words": sb["n_words"],
                "a_missing": sa["missing"],
                "b_missing": sb["missing"],
                "error": a.get("error") or b.get("error") or "",
            })
            print(json.dumps(live[-1]), flush=True)

    note = (
        "Static checks grade the compile-spec worked examples against the "
        "required recovery/split behavior. Live A/B is optional (`--live`) "
        "and needs `claude` on PATH."
    )
    if args.out:
        write_report(args.out, pairs, live, static_rows, note)
    print(json.dumps({"static": static_rows, "live": live}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
