---
name: aggregate-evidence
description: >-
  Builds a dataset of real examples of one behaviour pattern from chat exports,
  conversation logs, notes or references, applying a strict quality filter and
  writing records.jsonl plus a digest in the from-evidence contract. Use when
  the user says "aggregate evidence", "build a dataset from my chats",
  "collect examples of how I argue", "mine my exports for X", or wants raw
  conversations turned into evidence a skill can be built from.
---

# Aggregate evidence

Turn raw conversations into a dataset that `/distill-mindset` and `/forge-*`
can consume. Every record is a real exchange that shows the pattern. Nothing
in the output is invented.

## Inputs

Require all three. Stop and ask for whichever is missing.

1. **Pattern.** One sentence naming the behaviour. Sharpen it with
   [`references/pattern-definition.md`](references/pattern-definition.md)
   before reading a single source.
2. **Sources.** Paths to exports, logs, notes. Note the format of each.
3. **Subject.** Who the pattern belongs to. Their turns become `author: self`.

Do not build a dataset from a description of how someone behaves. That is a
spec without evidence; `/distill-mindset` refuses it too.

## Steps

1. Write the pattern definition (positive criteria, exclusions, three
   sample matches, three near-misses) to `datasets/<name>/digest.md` under
   `## Pattern`. Do this first so the filter is fixed before candidates arrive.
2. Scan sources. For each candidate exchange, capture the full turn sequence
   around the subject's turns, with timestamps. Keep enough partner turns to
   show what the subject was responding to.
3. Apply the quality bar in
   [`references/quality-bar.md`](references/quality-bar.md). Score 1 to 5.
   Drop anything under 3. Record why the top rejects were rejected.
4. Write each kept exchange as one record following
   [`references/record-schema.md`](references/record-schema.md). Fill
   `moves[]` with snake_case move names, `outcome`, and one or two sentences
   of `why_it_worked_or_failed`. Replace real names, handles and product
   names with role labels.
5. Choose held-out records: at least one in five, spread across partners
   and outcomes, quality 4 or 5. Put their ids in `dataset.json`
   `held_out_ids[]`. They are for evaluation only.
6. Write `dataset.json`, `records.jsonl`, `digest.md`. Set `record_count` to
   the real line count. Version `0.1.0` for a new dataset.
7. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py`. Fix every
   error before reporting.

## Digest contents

Counts (records, training, held out, partners, media, outcomes, quality
spread), moves by frequency, three to five sentences on what the records
show, and the rejected candidates with reasons. No quotes from rejected
material. No private detail beyond what a record needs.

## Privacy

- Partner names become role labels (`collaborator-a`, `reviewer`,
  `stranger`). Keep a private mapping outside the dataset if the user needs
  it.
- Strip product names, server names and links unless the pattern is about
  them and the user says they are public.
- A dataset that will ship in a plugin must be synthetic or consented.

## Done when

- `validate.py` passes.
- Every record scores 3 or higher and the held-out split is set.
- The digest names the pattern, the counts and the rejects.
- The user has the dataset path to hand to `/distill-mindset`.

For a large corpus, delegate the scan to the `evidence-aggregator` agent and
review its digest before accepting records.
