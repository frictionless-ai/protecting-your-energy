---
name: "review"
description: "Review whether future-capability claims are implemented and evidenced; find missing capabilities and fake generality without editing or running commands."
argument-hint: "[paths, diff, or capability plan]"
disable-model-invocation: true
disallowed-tools: ["Bash", "Edit", "Write", "NotebookEdit"]
---

# Review future capability

Requested review scope: $ARGUMENTS

Read:
- `${CLAUDE_PLUGIN_ROOT}/rules/policy.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/protocol.md`
- `${CLAUDE_PLUGIN_ROOT}/rules/verification.md`
- `${CLAUDE_PLUGIN_ROOT}/templates/handoff.md`

Enter protocol stage 5 directly in REVIEW mode. Inspect the named source and any
supplied plan/diff/logs. When intent must be inferred, label inferred scenarios and
keep conditional findings distinct from violations of an explicit promise.

Dispatch `speculative-generality:contract-challenger` once with a scoped packet,
actual source references, contracts and execution evidence if available. Do not
replay planning, execute tests, edit files, or repair findings in this mode.

Return concrete findings, capability/evidence gaps, and a status limited to the
reviewed batch. Request discriminating checks rather than pretending to run them.
No current caller or second implementation is NOT a defect. Conversely, merely
calling an interface "future-proof" is not proof of working future capability.

Report actual collaboration and verification limits. With no supported finding,
say so, but do not equate static inspection with passing runtime checks. Missing
native dispatch is a blocker unless the user agrees to a labeled fallback.
