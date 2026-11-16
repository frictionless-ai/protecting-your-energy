---
name: cli-full-md-install-agent
description: >
  Use this agent when running or resuming a ModSync CLI install from
  mod-builds/content/k1/full.md or content/k2/full.md on one live tree.
  Not for GUI, downloads, or writing the finished manual oracles.
---

Read `.agents/skills/cli-full-md-install/SKILL.md` first. Follow that skill only.

- One writer per tree. Run `bash .agents/skills/cli-full-md-install/scripts/one-writer-check.sh --game <dir>`.
- Guide is `content/k{1,2}/full.md`. Never `KOTOR*_Full.toml`.
- On failure, stop and hand off to `fail-closed-restore-agent` / `fail-closed-restore-replay`.
- Do not write `K1_manual` or `K2_manual`.
