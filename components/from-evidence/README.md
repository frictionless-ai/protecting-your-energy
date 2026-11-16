# from-evidence

First real artifact: `prove-the-effort` (skill) and `prove-the-effort-reviewer`
(subagent), forged from 112 real technical debates. See `CORRECTIONS.md` for
the checks the plugin gained from the user's corrections while forging it, and
`skills/forge-skill/references/design-principles.md` for the research-backed
gate every artifact passes.

Turn real conversations and examples into agent behaviour. A dataset of
exchanges becomes a mindset spec; the spec becomes a skill, a rule, a hook,
a subagent or a DESIGN.md; the output is scored against held-out examples;
adding examples regenerates it.

Status: **alpha 0.1.0**. The pipeline runs end to end on a synthetic
dataset. Provider adapters are templates. LLM-judged evaluation is a
rubric and an agent, not a script. Repository URL: TBD.

## Why

The generic `create-skill`, `create-rule`, `create-hook`,
`create-subagent` and `create-design-md` templates ask what the skill
should do and then write it from nothing. The result sounds like a
template because it is one. There is no phrase bank, no anti-pattern the
person actually avoids, no way to tell whether version two is closer to
them than version one, and no path for a good example found next week to
improve the skill.

This plugin puts evidence first. Every generator refuses to run without a
dataset or a spec. Every phrase in a generated skill is quoted from a
record and counted. Every anti-pattern names the phrases a wrong answer
would contain. Every build gets a scorecard. New examples go into the
dataset, and the build regenerates the skill.

## Pipeline

```
aggregate  →  distill  →  forge  →  evaluate  →  evolve
records       spec.md     SKILL.md   scorecard    + records, rebuild
```

| Step | Skill | Agent | Output |
|---|---|---|---|
| Aggregate | `/aggregate-evidence` | `evidence-aggregator` | `datasets/<name>/records.jsonl`, `dataset.json`, `digest.md` |
| Distill | `/distill-mindset` | `mindset-analyst` | `datasets/<name>/spec.md` |
| Forge | `/forge-skill`, `/forge-rule`, `/forge-hook`, `/forge-subagent`, `/forge-design-md` | `skill-author`, `provider-adapter` | `generated/<target>/<skill>/` or a rule, hook, agent, DESIGN.md |
| Evaluate | `/evaluate-fidelity` | `fidelity-judge` | `<skill>.scorecard.json` |
| Evolve | `/evolve` | (delegates to the user's `evolution` skill) | dataset version bump, rebuild, dated delta in the installed `EVOLUTION.md` |

Scripts, standard library only:

```bash
python3 scripts/validate.py                       # plugin structure + dataset contracts + build.json
python3 scripts/build.py                          # render every entry in build.json into generated/
python3 scripts/build.py --only disagree-with-evidence
python3 scripts/evaluate.py --skill-dir generated/claude/disagree-with-evidence --dataset datasets/_example
```

Build output is deterministic: same inputs, byte-identical files, no
timestamps. Dates appear only in `EVOLUTION.md` deltas a person writes.

## Install

Once published:

```
/plugin marketplace add <owner>/<repo>
/plugin install from-evidence
```

Until then, load it from a local checkout:

```
claude --plugin-dir /path/to/from-evidence
```

Requires Python 3.10 or newer for the scripts. No other dependencies.

## Dataset contract

```
datasets/<name>/
  dataset.json     {name, version, pattern, sources[], record_count, held_out_ids[]}
  records.jsonl    {id, source, medium, partner, ts, topic, turns[{ts, author, text}], moves[], outcome, why_it_worked_or_failed, quality}
  digest.md        counts, moves by frequency, what the records show, rejects
  spec.md          mindset/voice spec with fixed ## headings; parsed by build.py
```

`author` is `self` for the person being modelled. `partner` is a role
label, never a real name. `quality` is 1 to 5; only 4 and 5 are quoted.
`held_out_ids[]` are never quoted anywhere; they exist for evaluation.
Record contract and configured local storage are described in the [record schema](skills/aggregate-evidence/references/record-schema.md) and [integration guide](INTEGRATION.md).

The shipped dataset `_example` is synthetic (three invented exchanges, one
held out) and builds the skill `disagree-with-evidence`. It proves the
pipeline. The first real dataset will be a copy of a finished debate
dataset and will build the first real skill; neither is in this version.

## How adding examples regenerates a skill

1. `/evolve` writes the new exchange as a record, bumps the dataset
   version, updates the digest.
2. `/distill-mindset` recounts the phrase bank and anti-patterns.
3. `scripts/build.py` renders the templates again. Because the output is
   deterministic, `diff` shows exactly what the new evidence changed.
4. `/evaluate-fidelity` scores the new build against the old one on the
   held-out records. The new build must win or tie.
5. The rebuilt skill is installed over the old one. Its `EVOLUTION.md` gets
   one dated delta through the user's `evolution` skill (or by hand in the
   same format).

Nothing under `generated/` is edited by hand. If a generated skill reads
wrong, the fix is in the records, the spec or the templates.

## Provider targets

One canonical skill (`claude`). Adapters wrap it; they never restate it.

| Target | What is emitted | Install path (wrapper header repeats it) |
|---|---|---|
| claude | `SKILL.md`, `reference.md`, `EVOLUTION.md`, `dataset/bank.jsonl` | skill root |
| codex | canonical + `AGENTS.md` section | `~/.codex/skills/<skill>/` or `.codex/skills/<skill>/` |
| cursor | canonical + `<skill>.mdc` | `.cursor/skills/<skill>/` and `.cursor/rules/` |
| gemini | canonical + `GEMINI.md` section | `.gemini/skills/<skill>/` |
| copilot | canonical + `<skill>.instructions.md` | `.github/skills/<skill>/` and `.github/instructions/` |
| opencode | canonical + `AGENTS.md` section | `.opencode/skill/<skill>/` |

Templates live in `templates/providers/<target>/`. Alpha emits them as
written; beta verifies each layout against the provider's current docs.

## Layout

```
.claude-plugin/plugin.json   manifest
skills/                      nine skills; the ones with detail carry a references/ directory
agents/                      five subagents
datasets/                    contract + _example
templates/                   SKILL.md, reference.md, EVOLUTION.md, rule.md, agent.md, hooks.json, DESIGN.md, providers/
scripts/                     validate.py, build.py, evaluate.py, common.py
generated/                   build output (gitignored)
build.json                   which dataset builds which skill for which targets
EVOLUTION.md                 this plugin's dated delta log
```

## Deferred to beta

- Provider adapters verified against each tool's current docs, with
  install scripts.
- Automated LLM-judged evaluation runs (today: rubric + `fidelity-judge`
  agent, results pasted into the scorecard).
- `marketplace.json` for a multi-plugin repository.
- `build.py` rendering rules, hooks, subagents and DESIGN.md from a
  manifest (today: their `forge-*` skill fills the template in a session).
- A hooks entry that runs `validate.py` on dataset writes.

## License

MIT. See [`LICENSE`](LICENSE).
