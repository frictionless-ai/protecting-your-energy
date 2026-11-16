---
name: manual-vs-auto-diff
description: >
  Use this skill when comparing a finished CLI or GUI auto tree to the
  finished Holo manual oracle (after K1 step 185 or K2 step 144), or when
  the user asks for a semantic / official diff. Do not write the manual
  trees. Do not use mid-run as a parity verdict. Do not use for restore
  or for starting an install.
license: BSL-1.1
compatibility: Requires finished oracles at K1_manual / K2_manual and scripts/agents/diff_manual_vs_auto.sh.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Manual vs auto diff

## Checklist

- [ ] Auto lane finished the guide (K1 185, K2 144) **or** you label the report unfinished
- [ ] Manual trees stay read-only
- [ ] Run `scripts/agents/diff_manual_vs_auto.sh k1` or `k2` from the **repo root**
- [ ] Judge content, not patch counts

Load [references/judgment.md](references/judgment.md) when reading the report.

## Command

```bash
scripts/agents/diff_manual_vs_auto.sh k1
scripts/agents/diff_manual_vs_auto.sh k2
```

Output lands in `tmp/diff/`.

## Gotchas

- Two auto trees matching each other is not a match to the manual.
- Checkpoint names are not parity.
- Repo aliases: `kotor_manual_workdir/K1_manual` → hot `K1_manual`, same for auto; K2 content under `steamassets/`.
- A `.tpc` in auto with a same-stem `.tga` in the finished manual is the late dedupe class until that step has run — not a fail-closed rewind by itself.
- Loose store files must still exist after install (Copy, not Move).
