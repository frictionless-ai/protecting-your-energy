# Google / Gemini family

Fetched 2026-08-13. Apply on top of [generic.md](generic.md) when the
target matches `gemini` or `gemma`.

Sources: Gemini prompting-strategies, Gemini 3.5 Flash “what's new”,
thinking guide. The older Gemini 3 pages carry a deprecation notice;
do not cite them as the live page.

## Compile overlay

- Pick one delimiter and keep it consistent (Markdown or XML, not both).
  This named-target exception does not change portable-base.
- Direct, short, no persuasive padding. Verbose old prompt-engineering
  causes over-analysis.
- Put constraints, format, and the one-line identity at the **front**
  (system instruction or prompt head).
- Bulk recovered context, then a bridge (“Based on the information
  above…”), then the ask.
- Do not ask for visible chain-of-thought. Internal thinking is
  automatic. Optional “Think very hard” costs extra thinking tokens —
  do not write it.
- Do not set `temperature` / `top_p` / `top_k` on 3.x. Changing
  sampling degrades reasoning.
- Map hardness to host `thinking_level`: `minimal` chat/facts, `low`
  short agent loops, `medium` default (3.5 Flash), `high` hard
  math/code. Never `thinking_budget`.
- If the agent over-tools: lower `thinking_level` first, then one
  “limited action budget” line.
- Default voice is terse. Explicitly request length if the report must
  be long.
- Flash, time-sensitive tasks: state the current year. Optional
  knowledge-cutoff note (“January 2025”) only when the task is
  time-sensitive. Do not bake this into the generic core.
- Strict “answer only from the provided context” is extract-mode, not
  the default for implementation work.
- Preserve thought signatures across turns when the host requires it.
- Function results: matching ids; extra instructions belong on the
  function-result text, not a second user turn.

## What the Gemini example templates get wrong for this runtime

Some official example templates still say “Remember to think
step-by-step” and include a Plan/Execute/Validate ritual. That
contradicts the same page's “do not outline reasoning.” Do not copy
those templates wholesale. Effort knob + destination-over-route.
