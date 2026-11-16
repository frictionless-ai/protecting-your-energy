---
name: full-build-install-validation
description: >
  Use this skill when proving a full KOTOR build through the Avalonia
  wizard (select-all, fetch, ValidatePage dry-run/VFS) before a real
  write. Use even if the user says "run validation in the GUI" or
  "wizard full build." Do not use for CLI install from content/k1/full.md
  or k2/full.md (cli-full-md-install) or for unattended archive downloads.
license: BSL-1.1
compatibility: Requires .NET 9, a desktop/X11 session, ./mod-builds at repo root, and scripts/agents helpers.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Full-build install validation (GUI)

Read `docs/knowledgebase/modbuild-paranoia-doctrine.md` before touching a game directory.

## Checklist

- [ ] `./mod-builds` present
- [ ] Template dirs + `ensure_linux_holopatcher.sh`
- [ ] Launch via `local-desktop-gui-testing` helpers
- [ ] Select-all → fetch → `ValidatePage` → expand log
- [ ] Real install only if this task requires it and validation is acceptable
- [ ] One writer; fail-closed on errors (`fail-closed-restore-replay`)

Load [references/gui-workflow.md](references/gui-workflow.md) for the click sequence.

## Invariants (short)

1. Base must be proven factory-fresh.
2. Stop on error or doubt. Restore and replay; never append a missed step.
3. One writer per game directory (`pgrep`, not mtime).
4. Snapshot before each step.
5. Verify from the filesystem, not intent.
6. No silent skips.
7. Follow the guide literally.
8. Verify mod identity by content, not filename.

## Gotchas

- For guide-parity installs, CLI from `content/k{1,2}/full.md` is the default. This skill is the **wizard** path.
- `<<modDirectory>>` / `<<kotorDirectory>>` still apply in GUI flows.
- HoloPatcher missing from `Resources` is an environment failure, not a validation-logic failure.
