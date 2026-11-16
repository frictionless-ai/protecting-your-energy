---
name: distill-mindset
description: >-
  Produces a mindset and voice spec (language, behaviour, communication style,
  demeanor, motivations, moves, counted phrase bank, anti-patterns, held-out
  ids) from a from-evidence dataset. Use when the user says "distill the
  mindset", "write the voice spec", "what does this dataset say about how I
  argue", "turn these records into a spec", or after /aggregate-evidence
  finishes and before /forge-skill runs.
---

# Distill mindset

Read a dataset and write `spec.md` next to it. The spec is the only thing
`/forge-*` and `scripts/build.py` read about the person. Every claim in it
points at a record id.

## Input

A dataset directory that passes `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py`.
No dataset, no spec. If the user describes a person instead of pointing at
records, send them to `/aggregate-evidence` first.

## Steps

1. Read `dataset.json`, `digest.md` and every record. Split by
   `held_out_ids[]`. Read held-out records once for context, then set them
   aside. Nothing below quotes them.
2. Count. Moves per training record. `self` turns per record. Recurring
   phrases: any three-word-or-longer sequence that appears in two or more
   training records, plus one-off lines that name the move so well they are
   worth quoting (mark them n=1).
3. Fill the template in
   [`references/spec-template.md`](references/spec-template.md). Keep the
   exact `##` headings; `build.py` parses them. For each bullet, ask: which
   record shows this? If none, delete the bullet.
4. Write the phrase bank as `"phrase" (n=N; r-001, r-002)`. Count over
   training records only. Sort by count, then alphabetically. Quote exactly,
   including lowercase and typos.
5. Write anti-patterns as `never: <what> (markers: "a", "b")`. An
   anti-pattern is something the records show the person had the chance to
   do and did not. Markers are the phrases a wrong answer would contain.
   Every anti-pattern needs at least one record where the temptation was
   visible.
6. Write `trigger_description` in third person with quoted trigger phrases
   a user would actually say. It becomes the generated skill's frontmatter.
7. Copy `held_out_ids[]` into `## Held-out exemplars`.
8. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build.py --check`. Fix
   parse errors until it passes.

## Sections and what they hold

| Section | Holds | Test |
|---|---|---|
| Language | Word choice, sentence length, punctuation habits | Quote a fragment per bullet |
| Behaviour | What they do across the exchange | Name the move sequence |
| Communication style | Turn shape: questions per turn, quoting, endings | Count it |
| Demeanor | Tone under pressure | Point at the turn where pressure was highest |
| Motivations | What they are after; written so an answer can be checked against it | "Would this person answer this way?" must be decidable |
| Moves: opening / escalation / repair / exit | One bullet per move, imperative | Each maps to a `moves[]` name |

## Refuse

- A spec from memory of the person. Records or nothing.
- Traits without a record ("is thoughtful").
- Smoothing the voice. Typos and lowercase in the phrase bank stay.
- Quoting a held-out record anywhere in the spec.

## Done when

- `build.py --check` passes.
- Every phrase-bank line cites training record ids.
- Every anti-pattern has markers.
- The user has the spec path to hand to `/forge-skill`.

For a dataset over fifty records, delegate the counting to the
`mindset-analyst` agent and review its spec before accepting it.
