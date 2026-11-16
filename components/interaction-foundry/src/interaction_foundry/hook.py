"""Host-neutral stdin/stdout hook for mission-runtime supplemental context.

The hook reads a registry and request envelope, then emits advisory context.
It does not execute tools, change scheduling, or grant authority.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .intent import ResponsePlan
from .mission_runtime import prepare_handoff
from .registry import Registry


def _tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, ())
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{key} must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{key} must be a list of nonempty strings")
    return tuple(value)


def handle(payload: dict[str, Any], *, registry_path: str | Path) -> dict[str, Any]:
    """Compile one request envelope into JSON suitable for a pre-prompt hook."""
    if not isinstance(payload, dict):
        raise ValueError("hook input must be a JSON object")
    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("task_id must be a nonempty string")
    scopes = payload.get("scopes", {})
    if not isinstance(scopes, dict):
        raise ValueError("scopes must be an object")
    response_plan_payload = payload.get("response_plan")
    response_plan = (
        ResponsePlan.from_mapping(response_plan_payload)
        if response_plan_payload is not None else None
    )
    registry = Registry(str(registry_path), read_only=True)
    try:
        handoff = prepare_handoff(
            registry, task_id,
            query=payload.get("query", ""), scopes=scopes,
            hard_constraints=_tuple(payload, "hard_constraints"),
            learned_budget_bytes=payload.get("learned_budget_bytes", 0),
            now=payload.get("now"),
            dependencies=_tuple(payload, "dependencies"),
            completed_dependencies=_tuple(payload, "completed_dependencies"),
            preempted_by=payload.get("preempted_by"),
            applicability=_tuple(payload, "applicability"),
            compatibility=_tuple(payload, "compatibility"),
            response_plan=response_plan,
        )
        return {
            "schema": "interaction-foundry/hook-result/v1",
            "task": {
                "task_id": handoff.task.task_id,
                "registry_revision": handoff.task.revision,
                "runnable": handoff.task.runnable,
                "dependencies": list(handoff.task.dependencies),
                "completed_dependencies": list(handoff.task.completed_dependencies),
                "preempted_by": handoff.task.preempted_by,
            },
            "rule_ids": list(handoff.context.rule_ids),
            "learned_bytes": handoff.context.learned_bytes,
            "response_plan": (
                handoff.response_plan.as_dict()
                if handoff.response_plan is not None else None
            ),
            "additional_context": handoff.additional_context,
        }
    finally:
        registry.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    args = parser.parse_args(argv)
    result = handle(json.load(sys.stdin), registry_path=args.registry)
    json.dump(result, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
