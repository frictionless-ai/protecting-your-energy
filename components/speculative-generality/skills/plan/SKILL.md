---
name: "plan"
description: "Develop hypothetical future scenarios and implementable contracts through bounded role collaboration; return a plan without editing or executing."
argument-hint: "[task or subsystem]"
disable-model-invocation: true
disallowed-tools: ["Bash", "Edit", "Write", "NotebookEdit"]
---

# Plan future capability

Requested task: $ARGUMENTS

Treat the arguments as natural-language task context, never as a shell command.
If they are empty, use an unambiguous current task; otherwise ask for the target.
This workflow's authorization and preferences apply to this task only.

Read these files using their resolved plugin paths before proceeding:
- `${CLAUDE_PLUGIN_ROOT}/rules/policy.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/protocol.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/verification.md`
- `${CLAUDE_PLUGIN_ROOT}/templates/handoff.md`
- `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`

Run protocol stages 0–3 in PLAN mode. Use the actual namespaced plugin agents:
`speculative-generality:future-scout`, `speculative-generality:extension-architect`,
and `speculative-generality:contract-challenger`. Preserve independent initial
inputs, then relay structured scenario/contract proposals and a bounded challenge.

Do not execute commands, edit code, save a report, install anything, or provision a
service. Return the work record as PLANNED, NEEDS_DECISION, or BLOCKED. Include
accepted speculative capabilities, actual contracts, implementation and test routes,
unknowns, collaboration count, and the unaddressed frontier. No completed-build claims.

At most five advisory calls. Missing native dispatch is a disclosed blocker, not
permission to simulate collaborating agents. Follow the protocol's fallback rule.
