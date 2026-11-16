# Pattern definition

A pattern is one behaviour the subject repeats across partners and topics.
Write it down before reading sources, so the filter cannot drift toward
whatever turns up first.

## Shape

```markdown
## Pattern

Name: <two to four words>
One line: <what the subject does, when, and how it usually ends>

Matches when all of these hold:
- <observable criterion 1>
- <observable criterion 2>
- <observable criterion 3>

Excluded even when it looks similar:
- <near-miss 1 and why>
- <near-miss 2 and why>

Sample matches (from memory, before scanning; replace once real ones exist):
- <one line each, three of them>

Near-misses:
- <one line each, three of them>
```

## Criteria that work

- Observable in the text: a move the subject makes, a shape of sentence, a
  way an exchange ends.
- Independent of topic. "Asks for the measurement before arguing" matches
  in code review and in a dinner plan.
- Independent of mood. If a criterion only matches when the subject is
  annoyed, it is a mood, not a pattern.

## Criteria that do not work

- Traits ("is direct", "is thoughtful"). Not observable; every record could
  match or none.
- Outcomes alone ("wins the argument"). An outcome without the moves that
  produced it teaches nothing.
- Anything that needs the reader to know the subject personally.

## One pattern per dataset

If the sources show two patterns, build two datasets. A skill built from a
mixed dataset argues with itself.

## Held-out split

Pick held-out records before writing the spec. They should be typical, not
edge cases, so the evaluation measures the pattern and not its exceptions.
