from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

RESULTS = frozenset({"PASS", "FAIL", "UNKNOWN"})


def _canonical(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Job:
    kind: str
    inputs: dict[str, str]
    tool_versions: dict[str, str]
    params: dict

    @property
    def job_hash(self) -> str:
        return hashlib.sha256(_canonical(asdict(self)).encode()).hexdigest()

    def to_json(self) -> str:
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> Job:
        return cls(**json.loads(s))


@dataclass(frozen=True)
class Receipt:
    job_hash: str
    result: str
    outputs: dict[str, str]
    tool_versions: dict[str, str]
    conditions: str
    started: str
    finished: str
    worker: str = "local"

    def __post_init__(self) -> None:
        if self.result not in RESULTS:
            raise ValueError(f"invalid result: {self.result!r}")

    def to_json(self) -> str:
        return _canonical(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> Receipt:
        return cls(**json.loads(s))
