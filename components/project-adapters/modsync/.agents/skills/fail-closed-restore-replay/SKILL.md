---
name: fail-closed-restore-replay
description: >
  Use this skill when an install step fails, appearance.2da is 0 bytes,
  a snapshot hits ENOSPC, or anyone wants to install the missed step at
  the end. Restore the last good checkpoint, fix the cause, replay in
  guide order. Do not use for a finished-tree diff or a healthy resume
  that never failed.
license: BSL-1.1
compatibility: Requires the live tree's .modsync/checkpoints git repo. Do not write finished manuals.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Fail-closed restore, then replay

KOTOR full builds are last-writer-wins. Patchers append shared 2DA/TLK rows.
Installing an early step late looks successful and is still wrong.

## Checklist

- [ ] Identify last **good** SHA (not a known-bad pin)
- [ ] `bash scripts/restore-checkpoint.sh --checkpoint-dir DIR --sha SHA --game DIR --dry-run`
- [ ] Re-run with `--confirm` only after the dry-run looks right
- [ ] `appearance.2da` size is not 0 (also check `git cat-file -s`)
- [ ] Fix the cause, re-run N, replay N+1..end in guide order

Load [references/restore-protocol.md](references/restore-protocol.md) for the command sequence and hardlink trap.

If N is blocked (missing archive, CAPTCHA), **halt**. Do not skip. Do not backfill later.

Read `docs/knowledgebase/modbuild-paranoia-doctrine.md` before touching a game directory.

## Gotchas

- Checkpoint working trees can be **hardlinked** to live. A truncated live `appearance.2da` can show 0 on disk while `git cat-file -s SHA:Override/appearance.2da` is still 98324.
- `FileMode.Create` on a hardlinked dest truncates every link. Copy via temp + replace.
- Do not rewind to known-bad pins (zeroed 2DA, ENOSPC leftovers).
- After restore, relaunch **one** writer. See `cli-full-md-install`.
