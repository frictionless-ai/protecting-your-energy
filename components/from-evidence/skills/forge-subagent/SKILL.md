---
name: forge-subagent
description: >-
  Writes an agents/<name>.md subagent (frontmatter with example blocks, tools,
  system prompt) from a from-evidence spec so its voice, process and refusals
  come from records. Use when the user says "forge a subagent", "make an agent
  that reviews like me", "turn this spec into a subagent", "build a
  delegate from these examples", or wants a specialist agent whose prompt is
  grounded rather than generic.
---

# Forge subagent

A subagent is a skill with its own context and a delegation trigger. Build
it from the same spec a skill is built from, and add what only an agent
needs: when to delegate, which tools, what it returns.

## Evidence it consumes

A dataset with `spec.md`. Uses every section. `## Motivations` becomes the
agent's judgement, `## Moves` its process, `## Phrase bank` its voice,
`## Anti-patterns` its refusals. The records supply the `<example>` blocks:
a real partner turn becomes the `user:` line.

No spec, no agent. Send the user to `/distill-mindset`.

## Steps

1. Read the spec and two training records.
2. Decide delegation. Proactive (the parent should hand off without being
   asked) only when the records show the person doing this unprompted.
   Otherwise on request.
3. Pick tools. Read-only review agents get `Read`, `Grep`, `Glob`. Agents
   that write get `Write`, `Edit`. Agents that run checks get `Bash`. Do
   not give an agent a tool no record shows it needing.
4. Fill `${CLAUDE_PLUGIN_ROOT}/templates/agent.md`. Placeholders:
   `agent_name`, `agent_description`, two `example_N_*` sets, `color`
   (blue or cyan for review, magenta for generation, yellow for
   validation), `tools`, `agent_role`, `evidence_ref`, `responsibilities`,
   `process`, `voice`, `anti_patterns`, `output_format`.
5. Write the `<example>` blocks inside the `description` block scalar. Each
   `user:` line is a partner turn from a training record, names replaced.
   Each `<commentary>` names the record id and the move.
6. Quote the phrase bank verbatim under `## How this person talks`. Copy
   anti-patterns with tell-tale phrases under `## Never`.
7. Check no placeholder survived: `grep -n '{{' agents/<name>.md` prints
   nothing. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py`.
8. Run `/evaluate-fidelity` in agent mode: phrase-bank coverage and
   anti-pattern listing, same as a skill.

## Anti-patterns from evidence

The `## Never` section is the spec's anti-patterns. Add one agent-specific
line: never take an action a record shows the person deferring to someone
else. That keeps the agent's autonomy inside the evidence.

## Evolution hook

End the system prompt with: `Deltas: EVOLUTION.md next to this file. New
examples go to datasets/<name> via /evolve.` Regenerate from the spec when
the dataset version changes.

## Done when

- Frontmatter validates and both examples cite records.
- Tools match what the records show.
- The fidelity scorecard passes.
