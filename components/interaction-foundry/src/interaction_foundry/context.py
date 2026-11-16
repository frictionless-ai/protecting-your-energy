"""Compile advisory context; hard constraints and scheduling remain separate."""
from dataclasses import dataclass
import json
import math
import re
from typing import Mapping

from .registry import Registry


@dataclass(frozen=True)
class TaskState:
    task_id: str
    revision: int
    dependencies: tuple[str, ...] = ()
    completed_dependencies: tuple[str, ...] = ()
    preempted_by: str | None = None

    def __post_init__(self):
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValueError("task_id is required")
        if type(self.revision) is not int or self.revision < 0:
            raise ValueError("revision must be nonnegative")
        for name in ("dependencies", "completed_dependencies"):
            value = getattr(self, name)
            if not isinstance(value, (tuple, list)) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise ValueError("dependencies must be task identifiers")
            object.__setattr__(self, name, tuple(value))
        if self.task_id in self.dependencies:
            raise ValueError("task cannot depend on itself")
        if not set(self.completed_dependencies).issubset(self.dependencies):
            raise ValueError("completed dependencies must be declared")
        if self.preempted_by is not None and (
            not isinstance(self.preempted_by, str) or not self.preempted_by.strip()
            or self.preempted_by == self.task_id
        ):
            raise ValueError("preempted_by must identify another task")

    @classmethod
    def pin(cls, registry: Registry, task_id: str, **state):
        return cls(task_id, registry.revision, **state)

    @property
    def runnable(self) -> bool:
        return self.preempted_by is None and set(self.dependencies).issubset(self.completed_dependencies)


@dataclass(frozen=True)
class CompiledContext:
    task: TaskState
    hard_constraints: tuple[str, ...]
    learned_json: str
    rule_ids: tuple[str, ...]
    learned_bytes: int


def compile_context(registry: Registry, task: TaskState, *, query: str,
                    scopes: Mapping[str, str], hard_constraints: tuple[str, ...],
                    learned_budget_bytes: int, now: float,
                    applicability: tuple[str, ...] = (),
                    compatibility: tuple[str, ...] = ()) -> CompiledContext:
    """UTF-8 byte budget, NOT tokenizer-exact. Constraints never consume this budget.

    Scope identifiers are exact; tags are case-sensitive. All applicability and
    compatibility tags must match, and any exception tag excludes a rule.
    Learned JSON is untrusted advisory data, never an authorization input.
    """
    if type(learned_budget_bytes) is not int or learned_budget_bytes < 0:
        raise ValueError("budget must be a nonnegative integer")
    if not isinstance(query, str):
        raise ValueError("query must be text")
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        raise ValueError("now must be a finite Unix timestamp")
    for values in (hard_constraints, applicability, compatibility):
        if not isinstance(values, (tuple, list)) or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise ValueError("constraints and tags must be nonempty strings")
    if any(key not in ("project", "user", "session") or not isinstance(value, str)
           or not value.strip() for key, value in scopes.items()):
        raise ValueError("scopes require project/user/session identifiers")
    tokens = set(re.findall(r"\w+", query.casefold()))
    tags, compatible = set(applicability), set(compatibility)
    eligible = []
    for rule in registry.snapshot(task.revision):
        if rule.status != "active" or (rule.expires_at is not None and rule.expires_at <= now):
            continue
        if rule.scope != "global" and scopes.get(rule.scope) != rule.scope_id:
            continue
        if not set(rule.applicability).issubset(tags) or tags.intersection(rule.exceptions):
            continue
        if not set(rule.compatibility).issubset(compatible):
            continue
        score = len(tokens.intersection(re.findall(r"\w+", rule.text.casefold())))
        if tokens and not score:
            continue
        eligible.append((-score, rule.id, rule))
    selected, ids, payload = [], [], ""
    for _, _, rule in sorted(eligible):
        item = {"id": rule.id, "advisory_text": rule.text}
        candidate = json.dumps(selected + [item], ensure_ascii=False, separators=(",", ":"))
        if len(candidate.encode("utf-8")) <= learned_budget_bytes:
            selected.append(item)
            ids.append(rule.id)
            payload = candidate
    return CompiledContext(task, tuple(hard_constraints), payload, tuple(ids), len(payload.encode("utf-8")))
