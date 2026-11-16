# OpenAI family

Fetched 2026-08-13. Apply on top of [generic.md](generic.md) when the
target matches `gpt-5`, `gpt-4.1`, `gpt-4o`, `o1`, `o3`, `o4`, or
`codex`.

Sources: OpenAI prompting / prompt-engineering / prompt-guidance
(snippets where the full page timed out), Agents SDK define-agents +
orchestration, Codex AGENTS.md + best practices.

## Compile overlay

- Put the job and standing constraints in `instructions` / the
  developer role. The user message is this task plus any examples.
- Prefer `outputType` / Structured Outputs over “reply in JSON.”
- Lean: one copy of each rule. Internal coding-agent evals on the
  current lean-prompt guidance reported ~10–15% score up and 41–66%
  fewer tokens (official prompt-guidance snippets, 2026-08-13).
- Expose only the tools this commission needs; keep descriptions short.
- Name safe local actions once. Repeating “ask first” causes
  over-asking.
- Length via host `text.verbosity` when present, not prompt nagging.
  Current default models are already concise.
- Reasoning via host `reasoning.effort` (default medium) and
  `reasoning.mode=pro` only for high-value hard work. Not “think hard.”
- Split specialists only for different tools, approvals, or output
  type. `handoffDescription` is one concrete sentence.
- Handoff = the specialist owns the reply. `asTool` = the manager keeps
  the reply.

## Codex / AGENTS.md

If compiling for a Codex coding agent:

- Instruction chain: global override, then root → cwd. Later file
  wins. 32 KiB cap.
- Closest file wins; the user's current message overrides everything.
- Keep AGENTS.md short and accurate. Add a rule only after a repeated
  miss. Point at nested files instead of bloating the root.

## GPT vs reasoning models

GPT-class targets want more explicit how-to when the path is fragile.
Reasoning-class targets do not — extra how-to is noise. Default to
destination-over-route unless the family is a non-reasoning GPT and
the path is a narrow bridge (irreversible, schema-locked, or
integrity-critical).
