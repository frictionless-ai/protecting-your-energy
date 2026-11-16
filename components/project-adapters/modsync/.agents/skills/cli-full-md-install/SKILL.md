---
name: cli-full-md-install
description: >
  Use this skill when installing or resuming a KOTOR tree from
  mod-builds/content/k1/full.md or content/k2/full.md via ModSync CLI
  (Holo or Bio), even if the user says "oneshot", "parity run", or
  "keep going from the last step." Do not use for the Avalonia wizard,
  archive downloads, or prebuilt KOTOR*_Full.toml / KOTOR1_Full.md.
license: BSL-1.1
compatibility: Requires .NET 9, vendor HoloPatcher and/or BioPatcher, archives already on the store, one dedicated live tree.
metadata:
  author: ModSync
  version: "1.1"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# CLI install from the human guide

## Checklist

- [ ] Guide is `mod-builds/content/k1/full.md` or `k2/full.md` only
- [ ] One writer on the live tree (`bash scripts/one-writer-check.sh --game DIR`)
- [ ] DLL is not being rebuilt in-place while mapped
- [ ] Manual oracle is not a destination
- [ ] On failure → `fail-closed-restore-replay`
- [ ] After K1 185 / K2 144 → `manual-vs-auto-diff`

Load [references/trees-and-launch.md](references/trees-and-launch.md) for paths and argv.

## Policy

Guide interpretation goes through `guide-interpretation.defaults.toml` / `Policy.TryGetPattern`.
Do not add C# `if` for one published title. See `anonymous-mod-fixtures`.

## Gotchas

- Two writers may run **K1 Holo and K1 Bio** together only because they are different inodes. Same tree = abort.
- Prove writers with `pgrep`, not file mtime.
- Do not rebuild `src/ModSync.Core/bin/Debug/net10.0` while a writer has that DLL mapped. Use a git worktree or isolated `-o`.
- Extract scratch is chosen from the **destination path**. Do not share extract dirs across writers.
- Default `dotnet build` of Core can hang if the live process holds the output DLL.

## Scripts

- **`scripts/one-writer-check.sh`** — fail if another install already owns the game tree.
