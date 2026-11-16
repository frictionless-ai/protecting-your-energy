"""Explicit current-turn intent and response-plan contracts.

These records do not infer intent. A trusted host or reviewed extraction step
supplies them so the mission-runtime adapter can preserve response obligations
without granting new authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value.strip()


def _text_tuple(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        value = ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list of nonempty strings")
    result = tuple(_required_text(item, name) for item in value)
    if required and not result:
        raise ValueError(f"{name} must contain at least one item")
    return result


@dataclass(frozen=True)
class IntentFrame:
    subject: str
    requested_mode: str
    response_obligations: tuple[str, ...]
    secondary_intents: tuple[str, ...] = ()
    importance_signal: str | None = None
    source_event_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject", _required_text(self.subject, "subject"))
        object.__setattr__(self, "requested_mode", _required_text(self.requested_mode, "requested_mode"))
        object.__setattr__(self, "response_obligations", _text_tuple(
            self.response_obligations, "response_obligations", required=True
        ))
        object.__setattr__(self, "secondary_intents", _text_tuple(
            self.secondary_intents, "secondary_intents"
        ))
        for name in ("importance_signal", "source_event_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _required_text(value, name))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "IntentFrame":
        if not isinstance(payload, Mapping):
            raise ValueError("intent_frame must be an object")
        return cls(
            subject=payload.get("subject"),
            requested_mode=payload.get("requested_mode"),
            response_obligations=payload.get("response_obligations"),
            secondary_intents=payload.get("secondary_intents", ()),
            importance_signal=payload.get("importance_signal"),
            source_event_id=payload.get("source_event_id"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "requested_mode": self.requested_mode,
            "response_obligations": list(self.response_obligations),
            "secondary_intents": list(self.secondary_intents),
            "importance_signal": self.importance_signal,
            "source_event_id": self.source_event_id,
        }


@dataclass(frozen=True)
class ResponsePlan:
    intent: IntentFrame
    allowed_context_refs: tuple[str, ...] = ()
    forbidden_topics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_context_refs", _text_tuple(
            self.allowed_context_refs, "allowed_context_refs"
        ))
        object.__setattr__(self, "forbidden_topics", _text_tuple(
            self.forbidden_topics, "forbidden_topics"
        ))

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ResponsePlan":
        if not isinstance(payload, Mapping):
            raise ValueError("response_plan must be an object")
        return cls(
            intent=IntentFrame.from_mapping(payload.get("intent_frame")),
            allowed_context_refs=payload.get("allowed_context_refs", ()),
            forbidden_topics=payload.get("forbidden_topics", ()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "interaction-foundry/response-plan/v1",
            "intent_frame": self.intent.as_dict(),
            "allowed_context_refs": list(self.allowed_context_refs),
            "forbidden_topics": list(self.forbidden_topics),
            "authority": "This plan preserves response obligations but cannot authorize tools or external actions.",
        }
