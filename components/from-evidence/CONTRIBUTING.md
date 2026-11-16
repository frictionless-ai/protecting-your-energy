# Contributing

## Add a dataset

1. Create `datasets/<name>/`. Kebab-case name.
2. Write `dataset.json`, `records.jsonl`, `digest.md`, `spec.md` following
   [record schema](skills/aggregate-evidence/references/record-schema.md). Use the configured private dataset location described in [the integration guide](INTEGRATION.md). Or run `/aggregate-evidence`
   and `/distill-mindset` and let them write these.
3. Run `python3 scripts/validate.py`. Fix every error.
4. Add an entry to `build.json` and run `python3 scripts/build.py`.
5. Run `python3 scripts/evaluate.py --skill-dir generated/claude/<skill>
   --dataset datasets/<name>`.

Datasets that ship in this repo must be synthetic or consented. Partner
names are role labels. Real datasets stay local or in a private fork.

## Add examples to a dataset

Use `/evolve`, or by hand:

1. Append records to `records.jsonl`. New ids continue the sequence.
2. Update `record_count` and, if needed, `held_out_ids[]` in `dataset.json`.
3. Bump the dataset version (see below).
4. Update `digest.md` counts.
5. Re-distill `spec.md` so phrase counts are right.
6. `python3 scripts/validate.py && python3 scripts/build.py`.
7. Evaluate the new build against the previous one.

## Build and evaluate

```bash
python3 scripts/validate.py
python3 scripts/build.py
python3 scripts/evaluate.py --skill-dir generated/claude/<skill> --dataset datasets/<name>
```

Determinism check, run before any change to `scripts/` or `templates/`:

```bash
python3 scripts/build.py && find generated -type f | sort | xargs sha256sum > /tmp/a
rm -rf generated/* && touch generated/.gitkeep
python3 scripts/build.py && find generated -type f | sort | xargs sha256sum > /tmp/b
diff /tmp/a /tmp/b && echo deterministic
```

`claude plugin validate .` should also pass.

## Change a template

Templates are the only place generated wording lives. Edit
`templates/*.md` or `templates/providers/<target>/*`, rebuild, and read the
diff under `generated/`. A change here changes every generated skill, so
keep the diff small and say why in the commit.

## Versioning

- Plugin: semver in `.claude-plugin/plugin.json`. Patch for template
  wording and script fixes that do not change output shape. Minor for new
  skills, agents, placeholders or scorecard fields. Major for a record
  schema change.
- Datasets: semver in `dataset.json`, independent of the plugin. Patch for
  added records. Minor for a changed pattern or held-out split. Major for
  a record schema change.
- Generated skills carry `metadata.built-from: <dataset>@<version>` and
  `metadata.built-by: from-evidence@<version>`.

## Evolution log

`EVOLUTION.md` at the root holds dated deltas about how this plugin builds
skills. One reusable rule per entry, in the format shown there. Not a
changelog.

## Style

Skill bodies are instructions for Claude: imperative, one idea per
sentence, under 3,000 words, detail in `references/`. Descriptions are
third person with quoted trigger phrases. No buzzwords; `validate.py`
rejects a short list of them.

## Commits

One change per commit. Run `validate.py` and `build.py` before committing.
