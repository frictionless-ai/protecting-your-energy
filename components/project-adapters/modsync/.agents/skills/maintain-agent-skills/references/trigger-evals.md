# Trigger description evals

Load this when a skill is not activating, or is activating on the wrong tasks.
Source: https://agentskills.io/skill-creation/optimizing-descriptions

## Description rules

- Imperative: "Use this skill when…"
- User intent, not internals
- List contexts the user may not name
- Stay under 1024 characters
- Near-miss negatives belong in the description as "Do not use for…"

## Query set

Keep ~20 queries in `evals/trigger-queries.json`: 8–10 should-trigger, 8–10 should-not.
Include casual phrasing, typos, buried multi-step asks, and near-misses (shared keywords, different job).

Split ~60% train / ~40% validation. Do not tune on the validation set.

A query passes if trigger rate > 0.5 when `should_trigger` is true, else < 0.5.

Do not paste failed-query keywords into the description; generalize the category.
