# Classify

If a competent human collaborator could infer what the user is trying
to accomplish, this turn is not `skip`. One class per turn. Uncertain →
`skip` only when that collaborator could not recover the job either.
Casual register is never a reason to classify as `skip`.

| Class | When |
|---|---|
| `skip` | Acknowledgment (`thanks`, `ok`, `lgtm`); talk about the assistant; already names outcome, constraints, and a check; protected payload (bare slash, raw path, raw shell, session opt-out, autonomy-grant-only) |
| `mission` | Outcome-shaped end state ("make this reliable", "get it production-ready", "take ownership of", "clean up this codebase", "connect the dots" / "handhold itself"). A continue / not-done line with a live `.mission/` stays on this skill |
| `task` | A real job that would execute poorly if taken literally: fragments, deixis, corrections, frustrated debug, vague lookup, mixed style+task, a named micro-edit (usually `expansion: none`), or a bounded change that still needs compile |

`skip` does no compile. `task` compiles and delegates. `mission` writes
the operating contract and enters the control loop. Both `task` and
`mission` run infer-adjacent first.

A mid-mission user line is not a new classify. Normalize it and triage
with `amendment.md`.
