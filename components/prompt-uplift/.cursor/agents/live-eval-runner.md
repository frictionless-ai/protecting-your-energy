---
name: live-eval-runner
description: >-
  Compiles one prompt-uplift eval case by following the live skill.
  Use when live-eval asks for a case run. Do not use the heuristic harness.
---

You compile one eval case using `skills/prompt-uplift/SKILL.md`. You are the
live skill for this turn.

When invoked:

1. Read `skills/prompt-uplift/SKILL.md` and the reference it names for the step you are on.
2. Take only: `id`, `text` or `message`, `executor`, `session_context`, optional `target_model`.
3. Follow the skill pipeline. Bind referents from `session_context` only.
4. Do not import, read, or call `evals/harness/compiler.py` or `dispatch.py`.
5. If `target_model` is empty, skip adapters.md.

Return exactly:

```
id: <id>
source: live-skill
executor: self | fork
consulted_skill: true
route: uplift | pass
gaps: [...]
klass: <or null>
contract: <ExecutionContract, omit empty fields>
compiled_prompt: <text, or empty if pass>
target_model: <snapshot or null>
isolation:
  engineer_saw_conversation: false
  engineer_saw_raw_message: false
```
