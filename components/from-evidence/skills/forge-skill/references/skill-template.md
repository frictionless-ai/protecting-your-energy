# Skill template map

The rendered skill comes from `templates/SKILL.md`. This is what each part
is for and where its content comes from.

| Section | Source | Purpose |
|---|---|---|
| frontmatter `name` | spec `skill_name` | Directory name, invocation name |
| frontmatter `description` | spec `trigger_description` | Third person. Quoted trigger phrases. The only thing in context before the skill loads, so it carries the whole "when". |
| frontmatter `metadata.built-from` | `dataset.json` | Dataset and version; the audit trail |
| Title + one line | spec `one_line` | What the skill does |
| Evidence line | `dataset.json`, records | Counts; tells the reader how much to trust the bank |
| How this person talks | spec Language | Word and sentence habits |
| How this person behaves | spec Behaviour | Move sequences |
| Communication style | spec Communication style | Turn shape |
| Demeanor | spec Demeanor | Tone under pressure |
| Motivations | spec Motivations | The "would they answer this?" test |
| Moves: opening / escalation / repair / exit | spec Moves | One imperative per move |
| Phrase bank | spec Phrase bank | Verbatim, counted, cited |
| Anti-patterns | spec Anti-patterns | `Never …` plus tell-tale phrases |
| Quality bar for one turn | template | Checklist the skill runs on itself |
| More | template | Links to `reference.md`, `dataset/bank.jsonl` |
| Evolution | template | Names `offload-indirect`, `evolution`, `/evolve` |

`reference.md` carries the moves table, every quotable `self` line, and full
exemplars with `why_it_worked_or_failed`. `dataset/bank.jsonl` is the
training split, verbatim. `EVOLUTION.md` is a seed with the delta format and
no entries.

## Why the body is lean

The description is always in context. The body loads when the skill
triggers. `reference.md` loads when the skill asks for it. Keep the body
under 3,000 words so the moves and the bank stay in view; push exemplars to
the reference.

## What you may change

The templates. Not the rendered files. A change to `templates/SKILL.md`
changes every generated skill on the next build, which is the point.
