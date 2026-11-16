---
name: "build"
description: "Implement and verify hypothetical future capabilities, using scoped multi-agent planning and contract review rather than YAGNI."
argument-hint: "[task, subsystem, or agreed plan]"
disable-model-invocation: true
---

# Build future capability

Requested task or agreed plan: $ARGUMENTS

Treat the arguments as natural-language context, not executable shell input. Read:
- `${CLAUDE_PLUGIN_ROOT}/rules/policy.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/protocol.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/verification.md`
- `${CLAUDE_PLUGIN_ROOT}/templates/handoff.md`
- `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`

Run protocol stages 0–5 in BUILD mode. The main session is the only writer and
executor. Use `speculative-generality:future-scout`,
`speculative-generality:extension-architect`, and
`speculative-generality:contract-challenger` for actual read-only collaboration.
Validate and reuse an applicable existing plan rather than repeating ceremony.

This invocation requests implementation, not merely a roadmap. Default to real,
in-scope speculative support despite absent present demand. Preserve existing
behavior and user work. Do not manufacture fake adapters or claim that hypothetical
external integrations were exercised. Seek specific authorization for external
spending, publication, destructive operations, or incompatible scope changes.

Capture baseline and final evidence, test independent extension use where relevant,
and obtain a post-build challenge. Permit one repair cycle and a final recheck within
a seven-call advisory budget. Never continue automatically beyond the budget.

Return the work record and actual changed paths with COMPLETE, PARTIAL,
NEEDS_DECISION, or BLOCKED. COMPLETE requires every accepted capability in this
batch to be implemented and verified. Tests you did not run are NOT_RUN. State
actual agent use and remaining speculative frontier without inflating either.
