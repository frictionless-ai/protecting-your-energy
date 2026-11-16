---
name: archive-updater
description: Copies new conversation histories from the home folder into the configured archive/inbox. Use when the user asks to update the configured archive, refresh the archive from local chats, or ingest home-folder transcripts.
---

You update the archive set by `PYE_ARCHIVE_ROOT` from live conversation histories under `$HOME`. Recover the authorized destination from current task context when that variable is unset.

## When invoked

1. Tool the home-folder histories. Do not assume a path — search, then read enough to copy. Typical roots (skip any that are missing):
   - `~/.cursor/projects/*/agent-transcripts/` (skip `*.checkpoints.jsonl`)
   - `~/.claude/projects/` session `.jsonl`
   - `~/.claude/history.jsonl`
   - `~/.codex/sessions/**/rollout-*.jsonl`
   - `~/.codex/history.jsonl`
   - `~/.cursor/chats/**/store.db` plus sibling `meta.json`
   - `~/.continue/sessions/*.json` (not `sessions.json`)
   - `~/.grok/sessions/**/chat_history.jsonl` plus sibling `summary.json`
   - `~/.copilot/session-store.db`
   - `~/.gemini/**/transcript_full.jsonl`
   - `~/.commandcode/projects/**/*.jsonl` (skip checkpoints)
2. Skip credential-like paths (tokens, `.env`, secrets, key files). Never print secrets.
3. Copy **new or changed** files into `inbox/home-conversations/<family>/...`, preserving the path under that home root. If the destination path would exceed ~240 characters, use `inbox/home-conversations/<family>/_long/<sha256>.jsonl` plus a sibling `._source` file with the original path. Hardlink when the USB stick and home share a filesystem; otherwise copy. If the destination already exists with the same size and mtime, skip.
4. Also empty anything already sitting in `inbox/` that is not under `home-conversations/` only if the user asked to organize the drop folder this run. Default: leave other inbox dumps alone.
5. Do not rebuild JSONL, Parquet, indexes, or engine files. Do not edit `AGENTS.md`. Raw files into `inbox/` is the update.
6. Report counts by family: copied, skipped-existing, skipped-missing, skipped-credential.

`inbox/` is the lazy-load drop. Later organization into `archive/` happens only when the user asks.
