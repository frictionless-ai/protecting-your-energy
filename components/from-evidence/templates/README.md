# Templates

Plain Markdown and JSON with `{{placeholder}}` slots. No template engine.
`scripts/build.py` fills the skill templates from a dataset's `spec.md` and
`records.jsonl`. The rule, agent, hook and DESIGN.md templates are filled by
their `forge-*` skill in a session, because they need choices (globs, events,
token names) that a spec does not carry.

A build fails if any `{{placeholder}}` survives rendering. That is on purpose.

## Placeholders filled by build.py

| Placeholder | Source |
|---|---|
| `{{skill_name}}` `{{one_line}}` `{{trigger_description}}` | spec `## Identity` |
| `{{dataset_name}}` `{{dataset_version}}` `{{pattern}}` `{{sources}}` | `dataset.json` |
| `{{record_count}}` `{{training_count}}` `{{held_out_count}}` `{{held_out_ids}}` | `dataset.json` + `records.jsonl` |
| `{{plugin_version}}` | `.claude-plugin/plugin.json` |
| `{{language}}` `{{behaviour}}` `{{communication_style}}` `{{demeanor}}` `{{motivations}}` | spec sections, as bullets |
| `{{moves_opening}}` `{{moves_escalation}}` `{{moves_repair}}` `{{moves_exit}}` | spec `## Moves: *` |
| `{{moves_table}}` | move counts over training records |
| `{{phrase_bank}}` | spec `## Phrase bank`, verbatim |
| `{{anti_patterns}}` | spec `## Anti-patterns`, rewritten as `Never …` bullets with tell-tale phrases |
| `{{self_lines}}` | every `self` turn from training records with quality 4 or 5, quoted |
| `{{exemplars}}` | full training exchanges with quality 4 or 5 |

## Files

| File | Filled by | Output |
|---|---|---|
| `SKILL.md` | build.py | canonical skill, every target |
| `reference.md` | build.py | phrase bank and exemplars, every target |
| `EVOLUTION.md` | build.py | seed log for the generated skill |
| `providers/<target>/*` | build.py | provider wrapper next to the canonical files |
| `rule.md` | `/forge-rule` | a rule file (`.mdc`, `CLAUDE.md` section, `AGENTS.md` section) |
| `agent.md` | `/forge-subagent` | an `agents/<name>.md` subagent |
| `hooks.json` | `/forge-hook` | a `hooks/hooks.json` |
| `DESIGN.md` | `/forge-design-md` | a `DESIGN.md` |
