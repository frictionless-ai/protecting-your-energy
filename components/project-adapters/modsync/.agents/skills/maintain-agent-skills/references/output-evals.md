# Output quality evals

Load this after the skill triggers and you need to know if it improves results.
Source: https://agentskills.io/skill-creation/evaluating-skills

Author `evals/evals.json` (2–3 cases first). Each case: `id`, `prompt`, `expected_output`, optional `files`, later `assertions`.

Run each case with the skill and without (or vs a snapshot). Fresh context each run.

Workspace layout (sibling, not inside the skill if results are large):

```
<skill>-workspace/iteration-N/eval-<id>/{with_skill,without_skill}/
  outputs/  timing.json  grading.json
benchmark.json
```

Assertions must be checkable ("report includes a restore SHA"). Grade with evidence. Compare pass-rate delta vs token cost.

Give failed assertions, human feedback, and traces back into SKILL.md. Prefer fewer clearer steps over more rules.
