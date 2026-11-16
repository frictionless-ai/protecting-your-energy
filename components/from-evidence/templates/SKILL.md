---
name: {{skill_name}}
description: >-
  {{trigger_description}}
metadata:
  built-from: {{dataset_name}}@{{dataset_version}}
  built-by: from-evidence@{{plugin_version}}
---

# {{skill_name}}

{{one_line}}

why it helps: {{why_it_helps}}

{{benefits}}

when to use it: {{trigger_description}}

when not to: {{when_not_to_use}}

Built from dataset `{{dataset_name}}` v{{dataset_version}}: {{training_count}}
training records, {{held_out_count}} held out. Pattern: {{pattern}}. When a
rule here and a later delta in `EVOLUTION.md` disagree, the delta wins.

## rules, in order

Keep these six. Everything after them is background.

{{core_rules}}

## don't

Tell-tale phrases are markers a wrong turn would contain.

{{anti_patterns}}

## exchanges to copy the shape of

Verbatim from the records. Copy the shape of the `self` turns: length, where
the question lands, how the exchange ends.

{{inline_exemplars}}

## phrase bank

Verbatim. Quote these as written; do not invent new signature phrases.
Counts are over training records.

{{phrase_bank}}

## moves

One move per turn, named to yourself before writing.

### Opening

{{moves_opening}}

### Escalation

{{moves_escalation}}

### Repair

{{moves_repair}}

### Exit

{{moves_exit}}

## background

Read once. The rules above are what to do; this is why.

### Language

{{language}}

### Behaviour

{{behaviour}}

### Communication style

{{communication_style}}

### Demeanor

{{demeanor}}

### Motivations

{{motivations}}

## before sending one turn

- [ ] It follows rule 1 and breaks none of the six
- [ ] zero "don't" markers
- [ ] One move, one question
- [ ] Ends the way the exits above end

## more

- All exemplars and the moves table: [`reference.md`](reference.md)
- Training records: [`dataset/bank.jsonl`](dataset/bank.jsonl)

## evolution

This skill is living. A better example or a sharper rule found in a session
goes through the `offload-indirect` gate, then the `evolution` skill appends
one dated delta to [`EVOLUTION.md`](EVOLUTION.md). New examples go back into
dataset `{{dataset_name}}` through `/evolve`, which rebuilds this file. Do not
hand-edit the sections above; edit the evidence.
