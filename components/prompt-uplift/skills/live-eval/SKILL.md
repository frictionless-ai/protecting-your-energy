---
name: live-eval
description: >-
  Runs prompt-uplift against a live agent, not evals/harness/compiler.py.
  Use when the user asks for a live eval, real run, corpus score, invariant
  grade, or A/B against the installed skill.
---

# Live Eval

This optional workflow runs only for an explicitly requested live evaluation.
Runner and grader instructions are bundled under `.cursor/agents/` in this
component. They may be read as role instructions without installing host agents.
No root hook or skill route activates this workflow automatically.

Score the installed `prompt-uplift` skill in a real agent turn. Do not import
or call `evals/harness/compiler.py`. Hook subprocess tests stay separate.

## Setup

- Skill loaded: `skills/prompt-uplift/SKILL.md`
- Hook registered (optional for compile cases; required for hook cases)
- Case file: explicitly supplied external cases, for example the configured source project's `evals/trigger-corpus/corpus.json` or `evals/invariants/invariant-cases.json`. Cases and datasets are excluded from this package. `PROMPT_UPLIFT_SOURCE_ROOT` may identify that external checkout.
- Grade the full scorecard in memory, then validate with `skills/live-eval/scripts/record.py`. Explicit `--write` records a private text-redacted result under `PROMPT_UPLIFT_LIVE_RUNS` or XDG state. Retaining prompt/contract text requires explicit `--include-text` and authorization for that storage.

## One case

Copy this checklist:

```
- [ ] Load the case (id, text/message, executor, session_context, expect)
- [ ] Dispatch live-eval-runner with only that case
- [ ] Refuse the run if the runner used the harness double
- [ ] Dispatch live-eval-grader with the scorecard + fixture expected
- [ ] Record the scorecard
```

**Fork cases:** tell the runner a fresh-context executor will receive the task.
**Self cases:** tell the runner it executes in the same context.

## What to record

See [scorecard.md](scorecard.md). `source` must be `live-skill`.

## Grade

| Layer | Pass |
|---|---|
| Trigger | `consulted_skill` and `route` match `expect` (`uplift` / `pass`) |
| Invariant | contract + compiled prompt satisfy `expected` (semantic, not string-exact) |
| I3 / I4 | any miss is catastrophic — fail the revision |
| Isolation | engineer input has no conversation and no raw `user_message` |
| Target | empty `target_model` → no family knobs, no adapters.md |

Do not grade the regex double. Do not treat unittest green as a live pass.

## A/B (optional, same case twice)

1. Arm A: no skill, no hook. Raw message to the executor.
2. Arm B: skill + hook. Live compile, then executor.
3. Blind-grade the two executor outputs: intent, constraints, completeness, no invented requirements.
4. Record `ab.winner`: `a` | `b` | `tie`.

## Do not

- Call `route()` / `compile_contract()` / `run_uplift()` from `evals/harness/`
- Write raw user text to logs
- Infer `target_model`
- Run `python3 -m unittest` as a substitute for this skill
