# Quality bar

Score every candidate 1 to 5. Keep 3 and above. Quote only 4 and 5 into
generated skills (`scripts/build.py` enforces this).

| Score | Meaning |
|---|---|
| 5 | Full exchange. The pattern is unmistakable. The outcome is visible. A reader who has never met the subject could copy the moves. |
| 4 | Full exchange, pattern clear, outcome visible or strongly implied. Maybe one turn is missing context. |
| 3 | Pattern present but the exchange is truncated, or the outcome is unknown. Useful for counts and moves, not for quoting. |
| 2 | Pattern arguable. Could be read another way. Drop. |
| 1 | Not the pattern. Drop. |

## Checks per candidate

- Is the subject's turn a response to something visible in the record? If
  the partner's turn is missing, find it or score 3 at most.
- Does the exchange end? Look for the partner's last reaction. No ending
  means no `outcome`; score 3 at most.
- Would the subject be comfortable with this exchange quoted, once names
  are replaced by role labels? If not, drop it regardless of score.
- Is it a duplicate of an exchange already kept (same partner, same topic,
  same week)? Keep the higher-scored one.

## Moves

Name each move the subject makes, in order, as a snake_case verb phrase:
`ask_for_the_run`, `name_the_threshold`, `concede_out_loud`. Reuse names
across records. The moves table in the generated reference is only useful
when the names are consistent.

## Outcomes

One of: `conceded` (subject changed position), `convinced` (partner changed
position), `redirected` (both took a different path), `stalled` (no change,
exchange ended), `escalated` (tone got worse), `dropped` (one side left).

## Why it worked or failed

One or two sentences. Name the move that decided the outcome. This field is
the seed of the spec's move descriptions, so write it as a claim a future
reader can test against the turns.

## Rejects

Keep a list of the strongest rejects with the reason. They belong in
`digest.md`, without quotes. A pattern definition that rejects nothing is
too loose.
