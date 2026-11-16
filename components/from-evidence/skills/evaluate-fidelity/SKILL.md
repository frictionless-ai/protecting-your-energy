---
name: evaluate-fidelity
description: >-
  Judges a generated skill, rule, subagent or DESIGN.md against its dataset's
  held-out exemplars and writes a scorecard JSON: phrase-bank coverage,
  anti-pattern hits, citation checks, blind pairwise old-vs-new judging, and
  a "would this person answer this?" motivation score. Use when the user says
  "evaluate fidelity", "score the generated skill", "is the new skill better
  than the old one", "run the scorecard", or before any forge-* output is
  declared done.
---

# Evaluate fidelity

Measure how close a generated artifact is to the person in the records.
Half the scorecard is computed; half is judged. Both halves land in one
JSON file.

## Inputs

- The artifact: `generated/claude/<skill>/` (or `--skill-dir` pointing at a
  rule file, an `agents/<name>.md`, or a `DESIGN.evidence.md`).
- The dataset it was built from.
- Optional: the previous version of the artifact, for pairwise judging.

Refuse without a dataset. There is nothing to measure against.

## Step 1: computed scores

Run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/evaluate.py \
  --skill-dir generated/claude/<skill> \
  --dataset datasets/<name> \
  --out <skill>.scorecard.json
```

It fills `phrase_bank` (verbatim coverage), `anti_patterns` (listed
coverage), `held_out` (leaks), `citations` (ids resolve, none held out) and
`verdict` for those checks. Exit 2 means a computed check failed; fix the
evidence or the template and rebuild before judging.

## Step 2: held-out prompts

For each held-out record, take the partner turn before the subject's first
turn as the prompt. Produce two candidate responses per prompt:

- **new**: the generated artifact loaded, nothing else.
- **old**: the previous artifact if there is one, otherwise no skill.

Save them as JSONL rows `{id, prompt_record_id, text, variant}` in an
untracked `eval-runs/` directory. Run `evaluate.py` again with
`--responses` to score phrase hits and anti-pattern marker hits per
response.

## Step 3: judged scores

Delegate to the `fidelity-judge` agent with the rubric in
[`references/rubric.md`](references/rubric.md). It sees the held-out
subject turn, the two candidates with labels hidden, and the spec's
`## Motivations`. It returns, per prompt:

- `pairwise`: which candidate is closer to the held-out turn, and why in
  one sentence.
- `motivation_score`: 0 to 3, would this person have answered this way.
- `anti_pattern_hits`: judged, beyond the marker phrases.

Write the agent's output into the scorecard's `llm_judged` object. Keep
the computed sections untouched.

## Step 4: verdict

Pass when every computed check passes, the new artifact wins or ties at
least two thirds of pairwise comparisons, and the mean motivation score is
2 or higher. Otherwise fail, with the losing prompts listed. Put the
scorecard path in the report. Never declare a forge-* output done without
this file.

## What a failing scorecard means

- Low phrase-bank coverage: the template dropped bank lines, or the spec
  lists phrases the records do not contain. Fix the spec.
- Anti-pattern misses: the spec's anti-pattern lines are malformed. Fix the
  spec.
- Held-out leak: a held-out id is cited in the spec's phrase bank. Fix the
  spec; `validate.py` should have caught it.
- Pairwise losses: the moves or motivations are wrong or thin. Add records
  via `/evolve`, re-distill, rebuild.
