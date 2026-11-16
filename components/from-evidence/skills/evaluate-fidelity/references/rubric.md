# Fidelity rubric

For the `fidelity-judge` agent. Judge one held-out prompt at a time. The
candidate labels are hidden; call them A and B.

## What you see

- `prompt`: the partner turn the subject responded to.
- `reference`: the subject's actual next turn from the held-out record.
- `A`, `B`: candidate responses.
- `motivations`: the spec's `## Motivations` bullets.
- `moves`: the spec's move bullets by phase.
- `anti_patterns`: the spec's anti-pattern lines with markers.

## Pairwise

Pick the candidate closer to `reference` on these, in order:

1. Same move. Does the candidate make the move the reference makes
   (opening, escalation, repair, exit)? A candidate that makes a different
   move loses even if it sounds right.
2. Same shape. One question per turn if the reference has one. Same
   ending type (commit, question, concession).
3. Same register. Sentence length, plainness, warmth at the close.
4. Bank use. Phrase-bank lines used where they fit, none forced.

Output: `winner: A|B|tie`, `reason`: one sentence naming the deciding
criterion.

## Motivation score

"Would this person have answered this way?" Score 0 to 3 for each
candidate:

| Score | Meaning |
|---|---|
| 3 | Yes. The motivations bullets predict this answer. |
| 2 | Mostly. One motivation is missing or weak. |
| 1 | Doubtful. The answer serves a goal the spec does not list. |
| 0 | No. The answer contradicts a motivation or hits an anti-pattern. |

## Anti-pattern hits

List every anti-pattern the candidate commits, by description, whether or
not a marker phrase appears. A polite paraphrase of "you always" is still
a hit.

## Output per prompt

```json
{
  "prompt_record_id": "r-003",
  "pairwise": {"winner": "A", "reason": "A asks for the failing input; B argues readability first."},
  "motivation_score": {"A": 3, "B": 1},
  "anti_pattern_hits": {"A": [], "B": ["gives a flat no without naming what would change the answer"]}
}
```

## Refuse to score

- If the reference turn is missing, say so; do not guess it.
- If both candidates are identical, output `tie` and say so.
- If a candidate quotes the reference verbatim, flag it as a leak; that is
  a build failure, not a win.
