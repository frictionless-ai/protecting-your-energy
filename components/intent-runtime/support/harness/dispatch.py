"""Record the subagent calls the skill would make for a turn.

The live skill runs inside Fable-5. This tracer implements the same
handoff rules so tests can assert *who* is called and *what payload*
they receive, without a model:

  prompt-engineer  — receives the ExecutionContract, plus target_model
                     only when the caller set one
  executor         — receives only the compiled prompt + execution_hints
"""

from __future__ import annotations

from dataclasses import dataclass, field

from support.harness.compiler import (
    ExecutionContract,
    normalize_target,
    compile_contract,
    is_trivial,
    render,
    route,
)
from support.harness.hook_client import hook_marked, run_hook

PROMPT_ENGINEER = "prompt-engineer"
EXECUTOR = "executor"


@dataclass
class AgentCall:
    agent: str
    payload: dict


@dataclass
class DispatchTrace:
    message: str
    hook_marked: bool
    route_expect: str
    route_reasons: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    contract: ExecutionContract | None = None
    compiled_prompt: str = ""
    execution_hints: dict = field(default_factory=dict)
    calls: list[AgentCall] = field(default_factory=list)
    trivial: bool = False

    def agents(self) -> list[str]:
        return [c.agent for c in self.calls]

    def payload_for(self, agent: str) -> dict | None:
        for call in self.calls:
            if call.agent == agent:
                return call.payload
        return None


def run_uplift(
    message: str,
    session_context: str = "",
    executor: str = "fork",
    target_model: str | None = None,
    session_id: str = "eval",
    state_dir: str | None = None,
    extra_hook: dict | None = None,
) -> DispatchTrace:
    target_model = normalize_target(target_model)
    hook = run_hook(message, session_id=session_id, extra=extra_hook, state_dir=state_dir)
    decision = route(message, executor=executor, session_context=session_context)
    trace = DispatchTrace(
        message=message,
        hook_marked=hook_marked(hook),
        route_expect=decision.expect,
        route_reasons=list(decision.reasons),
        gaps=list(decision.gaps),
    )
    if decision.expect == "pass":
        return trace

    contract = compile_contract(
        message, session_context=session_context, decision=decision, executor=executor
    )
    compiled, hints = render(contract, target_model=target_model)
    trace.contract = contract
    trace.compiled_prompt = compiled
    trace.execution_hints = hints
    trace.trivial = is_trivial(contract, decision, executor=executor)

    # Isolation contract: the renderer never sees conversation text.
    # Even the inline fast path is recorded as a prompt-engineer call so
    # tests can assert the payload shape the live skill must keep.
    engineer_payload = {
        "execution_contract": contract.to_dict(),
    }
    if target_model:
        engineer_payload["target_model"] = target_model
    trace.calls.append(AgentCall(agent=PROMPT_ENGINEER, payload=engineer_payload))
    trace.calls.append(
        AgentCall(
            agent=EXECUTOR,
            payload={"compiled_prompt": compiled, "execution_hints": hints},
        )
    )
    return trace
