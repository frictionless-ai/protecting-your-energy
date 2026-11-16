---
name: forge-design-md
description: >-
  Writes a DESIGN.md from a from-evidence dataset of design decisions,
  reviews and reference screens, so every token and rule cites the record
  that established it. Use when the user says "forge a DESIGN.md", "document
  our design language from these reviews", "turn the design decisions into
  DESIGN.md", or wants persistent UI context for coding agents that is
  traceable to real decisions rather than reverse-engineered from CSS.
---

# Forge DESIGN.md

`DESIGN.md` records a design language. This skill builds it from decisions
people made and can point at, not from whatever values exist in the
stylesheet.

## Evidence it consumes

A dataset whose records are design decisions: `topic` names the surface or
token, `turns[]` hold the discussion, `moves[]` include the decision move
(`set_token`, `reject_variant`, `name_component_owner`, `state_rationale`),
`outcome` is `convinced` or `conceded`, and `why_it_worked_or_failed`
states the rule that came out of it.

Reference screens and repos may be cited as `sources[]` of kind `notes`.
They verify a value; they do not establish a rule on their own.

Two records per rule, or one record plus an existing `DESIGN.md` entry.

## Steps

1. Read the records. For each, extract role, value, scope, and the
   sentence that states the decision. Keep a private ledger with record
   ids.
2. Keep only what recurs or was decided explicitly. One mention of a colour
   in one review is not a token.
3. Fill `${CLAUDE_PLUGIN_ROOT}/templates/DESIGN.md`. Placeholders:
   `product_name`, `product_description`, `overview`, `sections`. Add
   `colors`, `typography`, `rounded`, `spacing` or `components` to the
   frontmatter only when a record names that system. Typography scales are
   mappings with `fontFamily`, `fontSize`, `lineHeight`, `fontWeight`,
   `letterSpacing` only.
4. Write Markdown sections in this order and only when supported:
   Colors, Themes, Typography, Layout, Elevation & Depth, Shapes,
   Components, Do's and Don'ts. Every sentence changes an implementation
   choice. A Don't needs a record with a stated prohibition.
5. Cite outside the document. `DESIGN.md` itself carries no record ids;
   write `DESIGN.evidence.md` next to it mapping each rule and token to
   record ids and the decision sentence.
6. Validate if the tooling is installed: `npx @google/design.md lint
   DESIGN.md`. If it is not installed, check the frontmatter shape by hand
   and say so in the report.
7. Run `/evaluate-fidelity` in design mode: every entry in
   `DESIGN.evidence.md` resolves to a record; no held-out record is cited.

## Anti-patterns from evidence

Do not promote a value that appears in code but in no decision record.
Do not write brand personality, audience or emotional rationale unless a
record states it. Do not invent token names to organise values.

## Evolution hook

New decisions go into the dataset via `/evolve`. Rebuild `DESIGN.md` and
`DESIGN.evidence.md` together. Preserve accepted decisions from the
previous version unless a newer record replaces them.

## Done when

- Every token and rule has a line in `DESIGN.evidence.md`.
- Frontmatter shape is valid.
- The fidelity scorecard passes.
