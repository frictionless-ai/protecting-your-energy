"""Description trigger-eval helpers.

Spec: https://agentskills.io/skill-creation/optimizing-descriptions
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from support.harness.skill_evals import CASE_ROOT, SKILLS

QUERY_KEYS = {"query", "should_trigger"}
OPTIONAL_QUERY_KEYS = {"id", "notes"}
ALLOWED_QUERY = QUERY_KEYS | OPTIONAL_QUERY_KEYS
TRAIN_FRACTION = 0.6
MIN_QUERIES = 16
MIN_EACH_LABEL = 6
STOP = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "what",
    "when",
    "want",
    "just",
    "only",
    "into",
    "your",
    "they",
    "them",
    "then",
    "than",
    "does",
    "don't",
    "dont",
    "about",
    "there",
    "their",
    "please",
    "would",
    "could",
    "should",
}


def queries_path(name: str, kind: str = "trigger") -> Path:
    filename = {
        "trigger": "trigger-queries.json",
        "train": "train_queries.json",
        "validation": "validation_queries.json",
        "holdout": "holdout_queries.json",
    }[kind]
    return CASE_ROOT / name / filename


def load_queries(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a JSON list")
    return data


def validate_queries(
    rows: Any, *, min_n: int = MIN_QUERIES, min_each: int | None = None
) -> list[str]:
    problems: list[str] = []
    if min_each is None:
        min_each = MIN_EACH_LABEL if min_n >= MIN_QUERIES else max(2, min_n // 3)
    if not isinstance(rows, list) or len(rows) < min_n:
        return [f"need at least {min_n} queries, got {0 if not isinstance(rows, list) else len(rows)}"]
    seen: set[str] = set()
    pos = neg = 0
    for i, row in enumerate(rows):
        prefix = f"[{i}]"
        if not isinstance(row, dict):
            problems.append(f"{prefix} must be an object")
            continue
        extra = set(row) - ALLOWED_QUERY
        if extra:
            problems.append(f"{prefix} unknown keys: {sorted(extra)}")
        query = row.get("query")
        if not isinstance(query, str) or not query.strip():
            problems.append(f"{prefix}.query must be a non-empty string")
        elif query in seen:
            problems.append(f"{prefix}.query is duplicated")
        else:
            seen.add(query)
        flag = row.get("should_trigger")
        if not isinstance(flag, bool):
            problems.append(f"{prefix}.should_trigger must be a boolean")
        elif flag:
            pos += 1
        else:
            neg += 1
    if pos < min_each:
        problems.append(f"need at least {min_each} should_trigger=true, got {pos}")
    if neg < min_each:
        problems.append(f"need at least {min_each} should_trigger=false, got {neg}")
    return problems


def split_queries(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[bool, list[dict[str, Any]]] = {True: [], False: []}
    for row in rows:
        groups[bool(row["should_trigger"])].append(row)
    train: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    for flag in (True, False):
        members = sorted(
            groups[flag],
            key=lambda r: hashlib.sha256(r["query"].encode()).hexdigest(),
        )
        n_train = max(1, round(len(members) * TRAIN_FRACTION))
        if n_train >= len(members):
            n_train = len(members) - 1 if len(members) > 1 else 1
        train.extend(members[:n_train])
        held.extend(members[n_train:])
    return train, held


def write_splits(name: str) -> None:
    rows = load_queries(queries_path(name, "trigger"))
    problems = validate_queries(rows)
    if problems:
        raise ValueError(f"{name}: " + "; ".join(problems))
    train, held = split_queries(rows)
    queries_path(name, "train").write_text(
        json.dumps(train, indent=2) + "\n", encoding="utf-8"
    )
    queries_path(name, "validation").write_text(
        json.dumps(held, indent=2) + "\n", encoding="utf-8"
    )


def description_of(name: str) -> str:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    if end == -1:
        return ""
    raw = text[4:end]
    lines: list[str] = []
    in_desc = False
    for line in raw.splitlines():
        if re.match(r"^description:\s*[>|]?-?\s*$", line):
            in_desc = True
            continue
        if in_desc:
            if re.match(r"^[A-Za-z0-9_-]+:", line):
                break
            lines.append(line.strip())
    return " ".join(s for s in lines if s)


def tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]{4,}", text.lower())
        if t not in STOP
    }


def near_miss_hits(description: str, rows: list[dict[str, Any]]) -> tuple[int, int]:
    """How many negatives share a content token with the description or a positive."""
    desc = tokens(description)
    pos_tok = set()
    for row in rows:
        if row.get("should_trigger"):
            pos_tok |= tokens(row["query"])
    pool = desc | pos_tok
    negatives = [r for r in rows if r.get("should_trigger") is False]
    hits = 0
    for row in negatives:
        if tokens(row["query"]) & pool:
            hits += 1
    return hits, len(negatives)


def to_activation_cases(rows: list[dict[str, Any]], skill: str) -> list[dict[str, Any]]:
    cases = []
    for i, row in enumerate(rows, start=1):
        cases.append(
            {
                "id": row.get("id") or f"{skill}-q{i:02d}",
                "family": "trigger-query",
                "class": "trigger-query",
                "expected": (
                    "should_trigger" if row["should_trigger"] else "should_not_trigger"
                ),
                "prompt": row["query"],
                "prior_turns": [],
                "platform": "trigger-eval",
            }
        )
    return cases
