---
name: prompt-uplift
description: >-
  Compiles a conversational user message into an explicit prompt (an
  ExecutionContract), dispatches it to the configured executor, and
  verifies the response against the contract. Use whenever a turn is marked
  PROMPT_UPLIFT_CANDIDATE by the runtime hook, and also whenever a user
  message is short, referent-dependent, or underspecified relative to the
  executor that will handle it — messages like "continue", "try again",
  "fix this", "make it better", a pasted log or screenshot with "please fix",
  a correction like "no, not that one" or "no kill it", or a large task
  stated in one casual sentence. Use even when the request seems simple:
  resolving what "it" refers to before delegating is this skill's job.
  Do not use for slash commands, raw command/path payloads, or when the user
  has asked not to have prompts rewritten.
arguments: [target_model]
---

# Prompt Uplift

Compile the user's conversational message into an executable prompt for the
target executor. The user keeps talking like a human; the executor receives an
engineered prompt; the user gets the outcome. Never change the intent,
authority, or scope of a request, and never turn an answer-request into an
action-request (or vice versa).

`$target_model` is optional. Use it only when the caller named a snapshot.
If it is empty, render the portable base template. Do not infer a model
from the session, the executor, or a default family. Do not open
[references/adapters.md](references/adapters.md). Do not mention other
models or their differences.

## Pipeline

**1. Route.** Decide why (or whether) this message needs uplift, using the
categorical reasons in [references/routing.md](references/routing.md).
Casual register (slang, lowercase, profanity, "pls") is never a reason by
itself. The test is: *can the actual target executor act correctly using the
context it will receive?* If you will execute in this same context yourself,
messages like "continue" are already complete — pass through and just do the
work. When routing is uncertain, pass through: forwarding the raw message is
always safer than forwarding a wrong guess.

**2. Resolve context.** You hold the conversation history, so binding
referents is your job — never a subagent's. Bind every "it", "that", "the
thing" to its concrete antecedent; collect environment facts (OS, versions,
paths) the session knows; neutralize frustration into a factual
previous-failures history. If a referent cannot be bound with confidence,
pass the message through unmodified.

**3. Compile the ExecutionContract** per
[references/execution-contract.md](references/execution-contract.md).
Honor its invariants: nothing synthesized may masquerade as a user statement;
never manufacture a motive the user didn't give; preserve the action mode
(answer vs. change) verbatim; preserve every negation and authority boundary.

**4. Classify constraints into channels** per
[references/constraint-channels.md](references/constraint-channels.md).
Task semantics and authority always reach the executor. Output-shape requests
render into the executor's prompt or its native generation controls. Never
silently drop a constraint. Constraints are turn-scoped unless the user used
explicit persistence language ("from now on", "always", "stop doing X").

**5. Render.** If `$target_model` is set, consult only that snapshot in
[references/adapters.md](references/adapters.md) and put native knobs
(effort, verbosity, schema, tool and context policy) in execution hints,
not in the prose. If `$target_model` is empty, render the portable base
template and emit no model-specific hints — skip adapters.md entirely.
For a trivial contract (single gap, executor is a local subagent), render
inline. For anything larger, delegate rendering to the prompt-engineer
subagent (see [agents/prompt-engineer.md](agents/prompt-engineer.md))
with the contract as its entire input — and `$target_model` only if the
caller set one. It must not see the conversation.

**6. Execute and check.** Dispatch to the executor. When the response
returns, check it against the contract: requested action honored, every hard
constraint and negation respected, response contract satisfied. On a
violation, re-ask the executor naming the specific deficiency — never edit
the answer's substance yourself. The only transformation you may apply is
additive: a one-line caveat noting an assumption the compiler made. A safety
refusal from the executor passes through as a refusal; never restyle it.

## Boundaries

- Pass through untouched: slash commands, raw shell/path payloads, sessions
  where the user opted out of rewriting, and messages that are complete for
  their executor.
- An autonomy grant ("you have permission, just do it all") is authority
  policy, not laziness — it must reach the executor, not trigger a rewrite of
  itself.
- Never log or restate raw user text outside this compilation flow; the
  contract lives in conversation state only.
