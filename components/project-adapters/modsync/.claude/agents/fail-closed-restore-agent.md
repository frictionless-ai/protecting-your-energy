---
name: fail-closed-restore-agent
description: >
  Use this agent when an install step failed and the live tree must be
  restored to the last good checkpoint, then replayed in guide order.
  Never install the missed step at the end.
---

Read `.agents/skills/fail-closed-restore-replay/SKILL.md` first.

Default to dry-run:

```bash
bash .agents/skills/fail-closed-restore-replay/scripts/restore-checkpoint.sh \
  --checkpoint-dir <game>/.modsync/checkpoints --sha <SHA> --game <game> --dry-run
```

`--confirm` only after the plan is right. Abort if `appearance.2da` is 0 bytes.
