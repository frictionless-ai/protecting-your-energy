#!/usr/bin/env python3
"""Description trigger-eval loop.

https://agentskills.io/skill-creation/optimizing-descriptions

  validate     check descriptions + query sets
  split        rewrite train/validation from trigger-queries.json
  print        show description lengths
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from support.harness.skill_descriptions import (  # noqa: E402
    description_of,
    load_queries,
    near_miss_hits,
    queries_path,
    validate_queries,
    write_splits,
)
from support.harness.skill_evals import list_skill_names  # noqa: E402


def _cmd_validate(_: argparse.Namespace) -> int:
    failed = 0
    for name in list_skill_names():
        desc = description_of(name)
        problems: list[str] = []
        if not desc.startswith("Use this skill when"):
            problems.append("description must start with 'Use this skill when'")
        if len(desc) < 1 or len(desc) > 1024:
            problems.append(f"description length {len(desc)} not in 1..1024")
        if not any(w in desc.lower() for w in ("skip ", "do not ", "don't ")):
            problems.append("description needs a skip / do-not boundary")
        for kind, min_n in (("trigger", 16), ("holdout", 6)):
            path = queries_path(name, kind)
            if not path.is_file():
                problems.append(f"missing {path}")
                continue
            problems.extend(
                f"{kind}: {p}" for p in validate_queries(load_queries(path), min_n=min_n)
            )
        trig = queries_path(name, "trigger")
        if trig.is_file():
            rows = load_queries(trig)
            hits, n_neg = near_miss_hits(desc, rows)
            if n_neg and hits < max(4, n_neg // 2):
                problems.append(
                    f"negatives look too easy ({hits}/{n_neg} share a content token)"
                )
        if problems:
            failed += 1
            print(f"{name}:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"{name}: description {len(desc)} chars, queries ok")
    return 1 if failed else 0


def _cmd_split(args: argparse.Namespace) -> int:
    names = [args.skill] if args.skill else list_skill_names()
    for name in names:
        write_splits(name)
        print(f"{name}: wrote train/validation")
    return 0


def _cmd_print(_: argparse.Namespace) -> int:
    for name in list_skill_names():
        desc = description_of(name)
        print(f"{name}\t{len(desc)}\t{desc[:80]}...")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate")
    p.set_defaults(func=_cmd_validate)
    p = sub.add_parser("split")
    p.add_argument("--skill")
    p.set_defaults(func=_cmd_split)
    p = sub.add_parser("print")
    p.set_defaults(func=_cmd_print)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
