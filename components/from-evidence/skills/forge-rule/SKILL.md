---
name: forge-rule
description: >-
  Writes a persistent rule file (Cursor .mdc, CLAUDE.md or AGENTS.md section)
  from a from-evidence dataset or spec, so every line cites a record or a spec
  section. Use when the user says "forge a rule", "turn this dataset into a
  rule", "make a standing rule from how I review", "add a rule grounded in
  these examples", or asks for coding standards or conventions backed by real
  corrections instead of a generic list.
---

# Forge rule

A rule is the always-on, short form of a skill: what to do and what never
to do, with no ceremony. Build it from evidence so it can be checked.

## Evidence it consumes

One of:

- A dataset with a `spec.md`. Use `## Behaviour`, `## Anti-patterns`, and
  the phrase bank.
- A dataset of corrections: records where `moves[]` includes a correction
  move (`reject_change`, `ask_to_revert`, `point_at_convention`) and
  `why_it_worked_or_failed` names the convention.

No evidence, no rule. A rule written from a chat description is the
generic template this plugin replaces.

## Steps

1. Read the spec or the correction records. List candidate rules. Each
   candidate needs two records that show it or one record plus a spec
   bullet.
2. Decide scope. Always-on rules go in `CLAUDE.md` / `AGENTS.md`. File
   scoped rules go in `.cursor/rules/<name>.mdc` with `globs`. Ask the user
   for globs if the evidence does not imply them.
3. Fill `${CLAUDE_PLUGIN_ROOT}/templates/rule.md`. Placeholders:
   `rule_description`, `globs`, `always_apply`, `rule_title`,
   `evidence_ref` (dataset name and version), `do_rules`, `dont_rules`,
   `examples`.
4. Cite. Every `Do` and `Do not` line ends with `(r-001, r-004)` or
   `(spec: Anti-patterns)`. Examples quote the record verbatim, names
   replaced by role labels.
5. Keep it under fifty lines. Split by concern if longer.
6. Check no placeholder survived: `grep -n '{{' <file>` must print nothing.
7. Run `/evaluate-fidelity` in rule mode: it checks that every cited id
   exists and that no held-out record is quoted.

## Anti-patterns from evidence

Write the `Do not` list from spec anti-patterns and from corrections in the
records. Include the tell-tale phrases. A `Do not` without a record behind
it is an opinion; leave it out.

## Evolution hook

Add a last line: `Deltas: EVOLUTION.md next to this file; new examples go to
datasets/<name> via /evolve.` The `offload-indirect` gate decides when a
child appends one.

## Done when

- Every line cites evidence.
- No placeholders remain.
- The fidelity scorecard passes.
