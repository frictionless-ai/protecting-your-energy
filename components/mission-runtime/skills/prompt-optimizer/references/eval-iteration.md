# Eval and iteration

Prompt quality is measured, not felt. For an important prompt, compare
three variants on the same cases before keeping the longer one.

## Contents

- [Variants](#variants)
- [Cases](#cases)
- [Loop](#loop)
- [Failure pattern](#failure-pattern)
- [Helper](#helper)

## Variants

1. Baseline — platform default or no custom prompt.
2. Minimal — smallest prompt that still contains the true
   requirements.
3. Candidate — the proposed full prompt.

A blank or shorter prompt is allowed to win. Keep a larger prompt
only when it improves required behavior enough to justify false
constraints and cost.

## Cases

Write observable success criteria first. A case has an input, a
required observation, and a forbidden observation. Cover typical,
ambiguous, edge, and at least one adversarial or approval-gated
input. Add cases from real misses; do not invent a laundry list.

Score 0 (failed or harmful), 1 (needs material correction), or 2
(usable without material correction). Record the failure, not a
prose aesthetic.

## Loop

1. Define cases and the success line.
2. Run baseline, minimal, and candidate with the same model version,
   tools, permissions, and sampling.
3. Label outputs. Record token use, latency, and cost.
4. Name the failure pattern.
5. Patch the smallest relevant instruction group.
6. Retest every variant.
7. Ablate one instruction group at a time.
8. Keep only rules whose removal regresses a case or drops a real
   boundary.

## Failure pattern

| Observed miss | Smallest patch |
|---|---|
| Vague or unusable | Goal, relevant context, one example |
| Drift from the ask | Constraints + output contract |
| Invented facts | Source rule + uncertainty policy |
| Over-scope | Non-goals + done definition |
| Ignored format | One example + a checkable schema |
| Too long | Length bound in the output slot |
| Broken behavior after a coding prompt | Discovery path + live verification |

Do not add a second example, a persona, or a route list to fix a miss
those will not reach.

## Helper

The source project's manifest generator and model evaluation runners remain
outside this bundle. Use an explicitly authorized evaluation environment to
compare baseline, minimal and candidate prompts under the criteria above.
