#!/usr/bin/env python3
"""Merge the local inspector, the hosted runner reviews, and the archive
waste evidence into one dashboard.

Three layers, weakest to strongest:

  archive    what the corpus says these patterns cost, in turns
  inspector  deterministic compiled-vs-raw scoring, runs with no CLI
  hosted     a real agent CLI answered both arms and a second agent graded
             them blind

The verdict prefers CLI evidence when it exists and falls back to the
inspector when no CLI was installed, so the page never claims a model result
it did not get.

Reads ids, scores, and the grader's one-line rationale. Does not copy fixture
message text or model replies. Stdlib only.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
WASTE = Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "archive-waste.json"


def _load_json_files(root: Path) -> list[dict]:
    found = []
    if not root.exists():
        return found
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        found.append({"path": str(path), "data": data})
    return found


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _hosted_rows(hosted: list[dict]) -> str:
    rows = []
    for h in hosted:
        host = h.get("host")
        for case in h.get("cases") or []:
            review = case.get("review") or {}
            cli = case.get("cli") or {}
            if review.get("graded"):
                winner = review.get("winner")
                blind = review.get("blind_map") or {}
                shown = f"A={blind.get('A')} B={blind.get('B')}"
                detail = review.get("why", "")
                rating = review.get("rating", "")
            else:
                winner = "—"
                shown = "—"
                rating = "not graded"
                detail = cli.get("reason", review.get("reason", ""))
            cls = "win" if winner == "compiled" else ("loss" if winner == "raw" else "")
            rows.append(
                "<tr>"
                f"<td>{_esc(host)}</td>"
                f"<td>{_esc(case.get('id'))}</td>"
                f"<td>{_esc(case.get('mined_class'))}</td>"
                f"<td class='{cls}'>{_esc(winner)}</td>"
                f"<td>{_esc(rating)}</td>"
                f"<td class='blind'>{_esc(shown)}</td>"
                f"<td class='why'>{_esc(detail)}</td>"
                "</tr>"
            )
    return "".join(rows)


def _waste_rows(waste: dict) -> str:
    rows = []
    for item in (waste.get("ranked_by_wasted_turns") or [])[:10]:
        rows.append(
            "<tr>"
            f"<td>{_esc(item.get('label'))}</td>"
            f"<td>{_esc(item.get('events'))}</td>"
            f"<td>{_esc(item.get('mean_gap'))}</td>"
            f"<td>{_esc(item.get('wasted_turns'))}</td>"
            "</tr>"
        )
    return "".join(rows)


def build(local: dict, hosted: list[dict], waste: dict) -> dict:
    wins = losses = ties = graded = 0
    for h in hosted:
        s = h.get("summary") or {}
        graded += int(s.get("cli_graded") or 0)
        wins += int(s.get("compiled_wins") or 0)
        losses += int(s.get("raw_wins") or 0)
        ties += int(s.get("ties") or 0)
    local_summary = local.get("summary") or {}
    if graded:
        positive = wins > losses
        evidence = "cli"
    else:
        positive = bool(local_summary.get("positive_use"))
        evidence = "inspector-only"
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": {
            "positive_use": positive,
            "evidence": evidence,
            "cli_graded": graded,
            "compiled_wins": wins,
            "raw_wins": losses,
            "ties": ties,
        },
        "local": local_summary,
        "reviews": local.get("reviews"),
        "hosted": [
            {"host": h.get("host"), "cli_found": h.get("cli_found"),
             "summary": h.get("summary"), "blinded": h.get("blinded")}
            for h in hosted
        ],
        "archive_evidence": {
            "totals": waste.get("totals"),
            "waste_rate": waste.get("waste_rate"),
            "top": (waste.get("ranked_by_wasted_turns") or [])[:10],
            "provenance": waste.get("provenance"),
        },
        "raw_text_written": False,
    }


def render_html(payload: dict, hosted: list[dict], waste: dict) -> str:
    rows = []
    for item in payload["reviews"] or []:
        rows.append(
            "<tr>"
            f"<td>{_esc(item['id'])}</td>"
            f"<td>{_esc(item['pattern'])}</td>"
            f"<td>{_esc(item['naive']['score'])}</td>"
            f"<td>{_esc(item['compiled']['score'])}</td>"
            f"<td>{_esc(item['delta'])}</td>"
            f"<td>{_esc(item['winner'])}</td>"
            f"<td>{_esc(item['rating'])}</td>"
            "</tr>"
        )
    v = payload["verdict"]
    s = payload["local"] or {}
    prov = (waste.get("provenance") or {}).get("caveat", "")
    banner = "The skill earns its place" if v["positive_use"] else "No lift yet"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>intent-runtime runner dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 70rem; }}
table {{ border-collapse: collapse; margin-bottom: 2rem; width: 100%; }}
td, th {{ border: 1px solid #bbb; padding: 0.35rem 0.6rem; text-align: left;
          font-size: 0.9rem; vertical-align: top; }}
th {{ background: #f2f2f2; }}
.verdict {{ padding: 0.8rem 1rem; border-radius: 6px; font-weight: 600;
            background: {'#e7f6e7' if v['positive_use'] else '#fdeaea'}; }}
.win {{ background: #e7f6e7; }} .loss {{ background: #fdeaea; }}
.why {{ font-size: 0.82rem; color: #444; }}
.blind {{ font-size: 0.78rem; color: #666; white-space: nowrap; }}
.note {{ color: #666; font-size: 0.85rem; }}
</style></head><body>
<h1>intent-runtime runner dashboard</h1>
<p class="verdict">{banner} — {_esc(v['compiled_wins'])} compiled wins,
{_esc(v['raw_wins'])} raw wins, {_esc(v['ties'])} ties across
{_esc(v['cli_graded'])} blind-graded CLI cases (evidence: {_esc(v['evidence'])}).</p>

<h2>What the archive says these patterns cost</h2>
<p class="note">Measured as constraint recurrence distance: the turns between a
constraint being stated and the user restating it while annoyed. "Mean turns
ignored" is the number the runtime is trying to drive to zero — carry the
constraint forward and the user never has to say it twice. {_esc(prov)}</p>
<table><tr><th>constraint class</th><th>restatements</th>
<th>mean turns ignored</th><th>turns in ignore span</th></tr>
{_waste_rows(waste)}</table>

<h2>Hosted runners — blind grading</h2>
<p class="note">Each case was answered twice by the host CLI, once from the raw
session and once from the compiled contract. A second CLI call graded the two
replies as A and B in shuffled order and never learned which was which. The
un-blinding is shown so the result can be checked.</p>
<table><tr><th>host</th><th>case</th><th>mined class</th><th>winner</th>
<th>rating</th><th>blinding</th><th>grader rationale</th></tr>
{_hosted_rows(hosted)}</table>

<h2>Local inspector A/B</h2>
<p class="note">Deterministic. Runs with no CLI installed, so CI always has a gate.
n={_esc(s.get("n"))} lifts={_esc(s.get("lifts"))} losses={_esc(s.get("losses"))}
avg_delta={_esc(s.get("avg_delta"))}</p>
<table><tr><th>id</th><th>pattern</th><th>naive</th><th>compiled</th>
<th>delta</th><th>winner</th><th>rating</th></tr>
{"".join(rows)}</table>
<p class="note">Generated {_esc(payload["generated_at"])}. No fixture text or model
replies are stored in this artifact.</p>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--waste", default=str(WASTE))
    args = ap.parse_args()

    blobs = _load_json_files(Path(args.artifacts))
    local = next((b["data"] for b in blobs if "reviews" in b["data"]), None)
    hosted = [b["data"] for b in blobs if b["data"].get("host")]
    if local is None:
        print("no local benchmark.json in artifacts", file=sys.stderr)
        return 2
    try:
        waste = json.loads(Path(args.waste).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        waste = {}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    payload = build(local, hosted, waste)
    (out / "dashboard.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (out / "dashboard.html").write_text(render_html(payload, hosted, waste), encoding="utf-8")
    print(out / "dashboard.html")
    print(json.dumps(payload["verdict"], indent=2))
    return 0 if payload["verdict"]["positive_use"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
