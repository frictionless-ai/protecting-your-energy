#!/usr/bin/env python3
"""Local A/B: naive message vs compiled contract, then inspector review.

Terminal-only. No GitHub. Writes JSON and a small HTML dashboard under
evals/local-runs/. Does not log raw prompt text — case ids and scores only
in the dashboard; fixture messages stay in the case file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from support.harness.inspector import review_case, summarize  # noqa: E402

CASES = (
    Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "cases.json",
    Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "session-patterns" / "archive-cases.json",
)
OUT_DIR = Path(os.environ.get("INTENT_RUNTIME_EVAL_DATA") or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "protecting-your-energy/intent-runtime/evals") / "local-runs"


def dashboard_html(payload: dict) -> str:
    rows = []
    for item in payload["reviews"]:
        rows.append(
            "<tr>"
            f"<td>{item['id']}</td>"
            f"<td>{item['pattern']}</td>"
            f"<td>{item['naive']['score']}</td>"
            f"<td>{item['compiled']['score']}</td>"
            f"<td>{item['delta']}</td>"
            f"<td>{item['winner']}</td>"
            f"<td>{item['rating']}</td>"
            "</tr>"
        )
    s = payload["summary"]
    verdict = "positive use" if s["positive_use"] else "no lift yet"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>intent-runtime local benchmark</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; }}
    td, th {{ border: 1px solid #444; padding: 0.4rem 0.6rem; }}
  </style>
</head>
<body>
  <h1>intent-runtime local benchmark</h1>
  <p>Generated {payload["generated_at"]}. Inspector scores compiled vs naive
  on session-pattern fixtures. Verdict: <strong>{verdict}</strong>.</p>
  <p>n={s["n"]} lifts={s["lifts"]} ties={s["ties"]} losses={s["losses"]}
  avg_delta={s["avg_delta"]}</p>
  <table>
    <tr>
      <th>id</th><th>pattern</th><th>naive</th><th>compiled</th>
      <th>delta</th><th>winner</th><th>rating</th>
    </tr>
    {"".join(rows)}
  </table>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        default=",".join(str(p) for p in CASES),
        help="comma-separated case files",
    )
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    cases = []
    for path in (p.strip() for p in args.cases.split(",")):
        if path:
            cases.extend(json.loads(Path(path).read_text(encoding="utf-8"))["cases"])
    reviews = [review_case(c) for c in cases]
    summary = summarize(reviews)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "reviews": [r.to_dict() for r in reviews],
        "raw_text_written": False,
    }
    dest = Path(args.out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "benchmark.json"
    html_path = dest / "dashboard.html"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(dashboard_html(payload), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(json_path)
    print(html_path)
    return 0 if summary["positive_use"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
