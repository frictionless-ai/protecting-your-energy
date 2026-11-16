# Spec template

Copy this into `datasets/<name>/spec.md`. Keep every `##` heading and its
exact text; `scripts/build.py` looks them up by name. Under `## Identity`,
lines are `- key: value`. Under every other heading, lines are `- ` bullets.
Prose between headings is ignored by the parser and fine for humans.

```markdown
# Mindset spec — <dataset name>

Distilled from `datasets/<name>` v<version> (training records <ids>; held
out <ids>).

## Identity
- skill_name: <kebab-case name of the generated skill>
- one_line: <what the skill does, one sentence, imperative>
- trigger_description: <third person; what it does and when; quoted trigger phrases the user would say>

## Language
- <word choice, sentence length, punctuation; quote a fragment>

## Behaviour
- <what they do across an exchange; name the move sequence>

## Communication style
- <turn shape: questions per turn, quoting, how turns end>

## Demeanor
- <tone under pressure; point at the turn>

## Motivations
- <what they are after, written so an answer can be judged against it>

## Moves: opening
- <imperative move, maps to a moves[] name>

## Moves: escalation
- <imperative move>

## Moves: repair
- <imperative move>

## Moves: exit
- <imperative move>

## Phrase bank
- "<verbatim phrase>" (n=<count over training records>; <record ids>)

## Anti-patterns
- never: <what the records show they never do> (markers: "<phrase a wrong answer would contain>", "<another>")

## Held-out exemplars
- <record id>
```

## Line formats the parser enforces

- Phrase bank: `"phrase" (n=2; r-001, r-002)`. The `; ids` part is optional
  but expected. Ids must be training records.
- Anti-patterns: `never: <description> (markers: "a", "b")`. Markers are
  optional but `evaluate.py` cannot score responses without them.
- Held-out exemplars: one id per bullet; must equal `dataset.json`
  `held_out_ids[]`.

## Placeholders the sections feed

`{{language}}`, `{{behaviour}}`, `{{communication_style}}`, `{{demeanor}}`,
`{{motivations}}`, `{{moves_opening}}`, `{{moves_escalation}}`,
`{{moves_repair}}`, `{{moves_exit}}`, `{{phrase_bank}}`, `{{anti_patterns}}`
and from Identity `{{skill_name}}`, `{{one_line}}`, `{{trigger_description}}`.
See `templates/README.md`.
