# Contributing

## Run the tests

From the repo root:

```bash
python3 -m unittest evals.test_subagent_dispatch -v
python3 evals/run_trace.py --all
```

These check hook marking, routing, and subagent payload shape. They do not
call a model.

Trigger-calibration and invariant grading are manual model runs. See
[the upstream evaluation guide](https://github.com/bodencrouch/prompt-uplift/blob/main/evals/README.md).

## Add a Reddit gold pair

Pairs live in `evals/reddit-pairs/pairs.json`. Source threads, grading
rules, and the add-a-pair steps are in
[the upstream source guide](https://github.com/bodencrouch/prompt-uplift/blob/main/evals/reddit-pairs/SOURCES.md).

Paraphrase OP and comment text. Do not store verbatim bodies or usernames.
After you add a pair, re-run the unittest and `python3 evals/run_trace.py --all`.

## Design docs vs runtime

[SKILLS.md](SKILLS.md) is the design rationale. Agents do not load it at
runtime. The installed skill is `skills/prompt-uplift/SKILL.md` plus the
files under `references/`. If the shipped code differs from the design,
that is recorded in [IMPLEMENTATION-NOTES.md](IMPLEMENTATION-NOTES.md).
