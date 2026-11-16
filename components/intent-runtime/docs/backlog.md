# Backlog

Small, independently-optional fixes surfaced by review, not yet worth their
own plan. Each was scored for priority by a dedicated review pass before
being logged here — see `ce-brainstorm` session, 2026-09-07.

## Vendor-dialect / named-target adapter follow-up

**Priority 2/10 · Not scheduled**

`references/models/google.md` notes Gemini's docs want one delimiter, not the
shipped Markdown+XML hybrid. No code path branches on `target_model` today —
`support/harness/compiler.py::render()` emits the same skeleton regardless, and
`target_model` is `None` in normal operation (opt-in only, nothing
auto-populates it). Building an adapter now would be speculative
future-proofing against a call path nothing exercises. Revisit only if
`target_model="gemini*"` shows up in real usage.

The referenced citation file `docs/research/prompt-engineering-sources-2026.md`
was never created — not "restored," despite the plan's wording.

