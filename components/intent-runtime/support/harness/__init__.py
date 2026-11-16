"""Deterministic stand-in for the intent-runtime compile pipeline.

The live skill runs inside Fable-5. This package implements the same
routing, contract, rendering, and subagent-handoff rules so CI can assert
who is called and what payload they receive, without a model.
"""

from support.harness.compiler import ExecutionContract, Route, compile_contract, render, route
from support.harness.dispatch import DispatchTrace, run_uplift
from support.harness.hook_client import run_hook

__all__ = [
    "ExecutionContract",
    "Route",
    "compile_contract",
    "render",
    "route",
    "DispatchTrace",
    "run_uplift",
    "run_hook",
]
