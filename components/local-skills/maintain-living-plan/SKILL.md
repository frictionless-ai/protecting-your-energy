---
name: maintain-living-plan
description: Maintain one active implementation plan and update it after each pass with concise landed/partial/next-step deltas. Use when planning evolves across iterations and older plans risk becoming stale.
---

# Maintain Living Plan

Keep one authoritative plan current through iterative implementation.

## Core Rule

After each substantial pass, update the active plan with three deltas:

1. Fully landed
2. Partially validated or uncertain
3. Recommended next-step changes

## Workflow

1. Identify the active plan file.
2. Confirm whether any competing plans are now stale.
3. Apply 3-delta update with minimal churn.
4. Mark superseded plans for merge/archive/delete.

## Output Snippet

```markdown
### Delta Update
- Landed:
- Partial:
- Next:
```

## Rules

- Do not maintain parallel \"current\" plans.
- Preserve history through concise updates, not plan sprawl.
- Keep updates decision-oriented, not narrative-heavy.
