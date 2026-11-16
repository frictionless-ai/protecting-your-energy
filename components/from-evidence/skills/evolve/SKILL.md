---
name: evolve
description: >-
  Appends new examples to a from-evidence dataset, bumps its version,
  re-runs distill and forge for the skills built from it, and writes the
  dated delta into the installed skill's EVOLUTION.md through the user's
  evolution mechanism. Use when the user says "evolve the skill", "add these
  examples to the dataset", "this exchange should teach the skill", "rebuild
  from the new evidence", or when offload-indirect has a reusable example for
  a generated skill.
---

# Evolve

Adding evidence regenerates the skill. This is the loop the plugin exists
for. Do not edit a generated file; edit the dataset and rebuild.

## Inputs

- A dataset name under `datasets/`.
- One or more new exchanges, or a delta already written by the `evolution`
  skill in an installed skill's `EVOLUTION.md`.

Refuse an example that fails the quality bar in
`skills/aggregate-evidence/references/quality-bar.md`, or that contains a
real name, handle or private detail.

## Steps

1. Write each new exchange as a record following
   `skills/aggregate-evidence/references/record-schema.md`. New ids
   continue the sequence; never reuse an id. Score quality. Decide whether
   the record joins the held-out split (keep the split near one in five).
2. Append to `records.jsonl`. Update `record_count` and `held_out_ids[]` in
   `dataset.json`. Bump the version: patch for added records, minor for a
   changed pattern or split.
3. Update `digest.md` counts and the moves table.
4. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py`.
5. Re-run `/distill-mindset` on the dataset. Recount the phrase bank; new
   records change counts and may add phrases or anti-patterns.
6. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build.py --only <skill>`
   for every `build.json` entry that uses the dataset.
7. Run `/evaluate-fidelity` with the previous generated version as `old`.
   The new build must win or tie. If it loses, the new records or the
   re-distilled spec are wrong; do not install.
8. Install the rebuilt skill over the old one, keeping the installed
   `EVOLUTION.md`.
9. Write the delta. Delegate to the `evolution` skill with the installed
   skill as the single target. The delta names the rule the new records
   taught, cites the record ids and the dataset version, and sets
   `promoted:` to today's date because the rule now lives in the rebuilt
   `SKILL.md`. If the `evolution` skill is not installed, append one entry
   in its format by hand:

   ```markdown
   ### YYYY-MM-DD
   - rule: …
   - why: …
   - example: r-NNN, dataset <name>@<version>
   - promoted: YYYY-MM-DD
   ```

10. Append one delta to the plugin's own `EVOLUTION.md` only when the
    change taught something about the pipeline, not about the person.

## Gate

The `offload-indirect` skill decides whether an example found mid-session
is worth this loop: reusable, one named target, sharper than what exists,
safe. If it passes, spawn a background child with this skill and the
dataset name. The parent keeps the user's task.

## Done when

- Dataset version bumped, `validate.py` passes.
- Rebuilt skill passes `/evaluate-fidelity` against the previous build.
- Installed `EVOLUTION.md` has one new dated delta.
