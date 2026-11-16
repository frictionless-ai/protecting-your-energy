# Session inference

If a competent human collaborator could infer what the user is trying
to accomplish from this short turn plus the last few, infer it too.

Read this on every `task` or `mission` after `context-recovery.md` when
the current message is short, corrective, repeated, or upset. The user
already implied the constraint. The time sink is the agent missing it.

## What a short upset turn means

A typical person can read "yeah do that but only fedora" after a
Windows-path answer and know the environment was already decided. The
runtime does the same. Frustration is not tone to strip. It is evidence
that the last compile dropped a load-bearing fact.

| Signal | What it is | Compile move |
|---|---|---|
| `frustration` | Upset register pointing at a miss | G5. Prior attempt goes in `previous_failures`. Bind every recovered constraint. Do not re-ask. |
| `repeat_ask` | Same job restated (`still broken`, `again`, `i told you`) | Same as frustration. The restated clause is `[stated]` and wins. |
| `correction` | `no`, `i meant`, `not that` | G2. Latest constraint supersedes. Record the old reading as `[stated, superseded]`. |
| `scope_pushback` | `i only asked`, `too much`, `don't rewrite` | Non-goals + `authority_not_granted`. Keep the original slice. |
| `do_it_already` | `just fix it`, `stop asking` | Action mode is `change` unless the original ask was explicitly answer-only. Autonomy grant. No new questions. |
| `restated_constraint` | Env or negation said again (`fedora`, `don't commit`) | Promote matching lines from recovered context into `hard_constraints`. |
| `missed_inference` | Frustration or repeat **and** bindable context | Fill `inferred_intent.direct_ask` from the bound job, not the outburst. |
| `still_not_done` | `you're still not done`, `where you left off` | G5. The last stop was early. Bind the named slice (audio, plan path). Done is an observable check. |
| `ceremony_continue` | `choose the next skill`, `pick for me`, `/lfg` plus English | G7. Do not ask which skill. Own the outcome until a real stop. A bare `/lfg` with no extra words stays pass-through. |
| `verify_surface` | `webui`, `confirm everything`, dogfood, browser | Success condition is a browser or audio check, not a claim. MCP writes and the studio UI stay consistent `[entailed]`. |
| `self_handhold` | `connect the dots`, `handhold`, `follow up` as a complaint, `iterate until`, `check it yourself`, `tired of telling` | G5. The user is driving the agent's loop. Bind recovered facts, generate follow-ups, iterate until an observable check, and do not hand the loop back. |

Casual register without one of these signals is not a rewrite reason.

## Recovery that the last turn already paid for

When any signal above fires and `session_context` has environment,
toolchain, OS, desktop, or a negation, copy those facts into
`hard_constraints` / `negations`. Do not wait for the user to type them
a third time.

Standing project files (`AGENTS.md`, `CLAUDE.md`, `STRATEGY.md`) are
recovered by path: "read before acting." Do not paste them.

A restated constraint after the agent already had it is the main
time sink in the personal archive. Read `preference-recovery.md`
and bind from the record instead of asking again.

## What not to invent

Do not invent a motive for the outburst. Do not flip answer vs change
except for `do_it_already` after an explanation-shaped last turn. Do not
broaden scope because the user is upset — scope_pushback is the opposite.

## Research that this layer already owns

Public prompt-improvers rewrite the user's words or ask a stack of
questions. This runtime marks, binds, and executes. The hook stays
content-free. The engineer still never sees the conversation. Hybrid
emission (Markdown slots, XML only around recovered user data, Python
shape only for branching routing) lives in `compile-spec.md`.
