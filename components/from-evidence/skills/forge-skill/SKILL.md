---
name: forge-skill
description: >-
  Generates a SKILL.md, reference.md, dataset bank and EVOLUTION.md seed from a
  from-evidence spec and dataset, with a verbatim phrase bank, explicit
  anti-patterns, an evolution hook and per-provider variants for Claude, Codex,
  Cursor, Gemini, Copilot and OpenCode. Use when the user says "forge a skill",
  "build the skill from this dataset", "generate a skill from the spec",
  "make a skill that argues like me", or wants a skill grounded in real
  examples instead of a blank template.
---

# Forge skill

Render a skill from evidence. The skill's voice, moves, phrase bank and
anti-patterns come from a dataset's `spec.md` and training records. You do
not write them; you check them.

## Input

Required: a dataset directory with a `spec.md` that passes
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build.py --check`.

No dataset or spec means no skill. Do not draft a persona from a
description, a name, or memory. Point the user at `/aggregate-evidence` and
`/distill-mindset`.

## Steps

1. Read the spec. Read two training records. If the spec makes a claim no
   record supports, fix the spec first (that is `/distill-mindset` work).
2. Add or confirm the entry in `${CLAUDE_PLUGIN_ROOT}/build.json`:
   dataset name, `kind: skill`, the `skill_name` from the spec, and the
   target list. `claude` is always included; it is the canonical output.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build.py --only <skill>`.
   Output lands in `generated/<target>/<skill>/`.
4. Read the generated `SKILL.md` against
   [`references/prompt-engineering-rules.md`](references/prompt-engineering-rules.md).
   The template already follows them; what you check is the content the
   spec put in: trigger phrases a user would say, moves in imperative form,
   a phrase bank that reads as the person, anti-patterns that are testable.
5. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/evaluate.py --skill-dir
   generated/claude/<skill> --dataset datasets/<name>`. Fix anything under
   threshold by editing the spec or the records, never the generated file.
6. Run `/evaluate-fidelity` for the LLM-judged parts. Do not declare the
   skill done without a scorecard.
7. Install: copy `generated/claude/<skill>/` to the user's skill root. If
   an `EVOLUTION.md` already exists there with deltas, keep it. Other
   providers install from `generated/<provider>/<skill>/`; each wrapper's
   header says where.

## What the output contains

See [`references/skill-template.md`](references/skill-template.md) for the
section map. In short: third-person trigger description, one-line goal,
evidence line (dataset, version, counts), language, behaviour, style,
demeanor, motivations, moves by phase, verbatim phrase bank with counts,
anti-patterns with tell-tale phrases, a per-turn quality bar, links to
`reference.md` and `dataset/bank.jsonl`, and the evolution hook.

## Providers

One canonical skill. Adapters wrap it; they never restate it. A provider
directory holds the canonical files plus one wrapper (Codex `AGENTS.md`
section, Cursor `.mdc` rule, Gemini `GEMINI.md` section, Copilot
`.instructions.md`, OpenCode `AGENTS.md` section). Do not hand-edit a
wrapper; edit `templates/providers/<target>/` and rebuild. The
`provider-adapter` agent handles installs into several tools at once.

## Refuse

- Writing the skill body by hand. Edit evidence, rebuild.
- Adding a phrase the records do not contain.
- Removing an anti-pattern because it feels harsh.
- Declaring done without `evaluate.py` and `/evaluate-fidelity`.

## Done when

- `build.py` and `evaluate.py` pass.
- A scorecard from `/evaluate-fidelity` exists.
- The install path and the dataset version are in the report.
