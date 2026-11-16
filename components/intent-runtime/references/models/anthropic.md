# Anthropic / Claude family

Fetched 2026-08-13. Apply on top of [generic.md](generic.md) when the
target matches `claude`, `fable`, `mythos`, `opus`, `sonnet`, or `haiku`.

Sources: C4BP, Sonnet 5 / Opus 5 / Fable 5 prompting pages, Agent Skills
overview + best practices, code.claude.com/docs/en/skills, context
engineering (2025-09, still cited), MARS (2025-06, still cited).

## Shared Claude core

- Be explicit about output, constraints, and *why*. Treat the model as a
  brilliant new employee with no conversation you have not written down.
- Long documents at the top; query last. The “up to 30%” claim is
  response quality on complex multidocument inputs.
- XML or Markdown sections to delimit instructions / context / examples
  / user input. 3–5 diverse examples beat a laundry list of edge cases.
- One-sentence role in the system / identity slot for tone. Not a
  quality lever for facts.
- Prefer “do X” over “don’t do Y.” Latest models overtrigger on
  “CRITICAL / YOU MUST” — use normal language.
- Prefills are unsupported on 4.6+; use Structured Outputs or system
  instructions for locked formats.
- Adaptive thinking + host `effort` replace `budget_tokens`.
- Parallel independent tool calls; sequential when a later call needs
  an earlier result.
- Do not instruct the model to transcribe internal reasoning into the
  user channel (triggers a reasoning-extraction refusal on Fable 5).

## Family differences

Verification is the load-bearing split. Do not collapse these into one
rule.

### Fable 5 (and Mythos 5; same prompting page)

- Brief instructions steer; give intent/why, not only the request.
- State boundaries (do not fix until asked; do not take unrequested
  actions).
- Long-horizon: make self-verification **explicit**. Fresh-context
  verifier subagents outperform self-critique. Instruct an interval and
  “verify against the spec in a fresh context.”
- Audit every progress claim against a tool result.
- Use parallel subagents frequently; prefer async; keep working.
- Prior-model skills are often too prescriptive and can degrade quality.
  Strip scaffolding; raise host effort instead of adding procedure.
- Do not surface remaining-token countdowns (context-budget anxiety).

### Opus 5

- Give the full spec in the first turn, then leave it to run.
- **Remove** explicit verification / “use a subagent to verify” /
  “double-check.” They cause over-verification at no quality gain.
- Do not spawn a subagent to verify the same agent's own work.
- Cap delegation; it delegates too readily. Prefer one worker over
  several unless work is large and parallelizable.
- Effort controls thinking volume, not visible length — prompt for
  conciseness if the report must be short.
- Constrain scope: it can quietly widen the task.

### Sonnet 5

- Literal instruction following, especially at lower effort. It will
  not generalize “do this to item 1” to unnamed items. Name the scope.
- Under-thinking at low effort: raise host effort; do not prompt around
  it.
- Review prompts that say “only high-severity” silently drop bugs. Ask
  for coverage + confidence; filter later.
- Progress-update scaffolding (“summarize every N tools”) is often
  removable.
- Put the full spec in the first turn; progressive underspec wastes
  tokens.

## Portable verification rule for this runtime

The orchestrator decides whether a consequential change needs an
independent non-authoring check. That decision is routing, not skill
prose. When compiling **for** Fable 5 on a long run, the compiled spec
may name a fresh-context check against the spec. When compiling **for**
Opus 5, omit that sentence. When compiling **for** Sonnet 5 review
tasks, require coverage-then-filter, not “only high-severity.”
