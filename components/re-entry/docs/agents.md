# Agents

`reentry setup` does two things. It runs REA's own setup for MCP registration, and it installs the six re-entry skills where each agent looks for personal skills. REA already owns agent detection, config backups, atomic writes, dry-run plans and uninstall for Claude Code, Codex, Cursor, Gemini CLI, OpenCode, Copilot CLI, Grok Build, Qwen Code and others. Re-entry does not duplicate that.

## What `setup` runs

```
npx -y rea-agents@latest setup --client <id> ... [--dry-run]
```

with the same `--client` flags you passed, or `--all-detected` when you passed none. REA writes a `type: "stdio"` entry named `rea` that launches `npx -y rea-agents@<pinned> mcp`, pinned to the version that ran setup. It backs up every file it touches and keeps the first `.rea.backup` snapshot. Then re-entry copies `.agents/skills/*` to the skill destinations below.

`--dry-run` passes through to REA and prints re-entry's own plan. Nothing is written.

`--uninstall` runs `rea uninstall` for the same clients and removes only re-entry-owned skill directories, symlinks and pointer files.

## Skill destinations

REA's convention, which re-entry follows:

| Agent | Skills folder |
|---|---|
| Claude Code | `~/.claude/skills/` (or `$CLAUDE_CONFIG_DIR/skills`) |
| Gemini CLI | `.agents/skills` under its selected home |
| Everything else (Codex, Cursor, OpenCode, Copilot CLI, Qwen Code, Grok Build) | `~/.agents/skills/` |

When `~/.agents/skills/` exists, re-entry installs there once and symlinks the Claude Code folder to it. That matches how this machine already shares skills (`~/.agents` is authoritative; `~/.agents/bin/sync-claude.sh` mirrors by symlink). On a machine without `~/.agents`, each destination gets a plain copy.

Pointer files, so an agent opening a project finds the rules: `.cursor/rules/reverse-anything.mdc` for Cursor; `CLAUDE.md` and `GEMINI.md` in this repo are one-line pointers at `AGENTS.md`.

## Claude Code plugin

Claude Code users can skip the CLI:

```
claude plugin marketplace add bodencrouch/re-entry
claude plugin install re-entry@re-entry
```

`.claude-plugin/plugin.json` registers the `rea` MCP server with the same `npx -y rea-agents mcp` shape and exposes `skills/` and `commands/`. `reentry setup` checks `~/.claude/plugins/installed_plugins.json` and skips Claude Code writes when the plugin is already installed, so a user never ends up with two `rea` registrations.

## Manual registration

If your agent is not covered, add the server block REA documents:

```json
{ "mcpServers": { "rea": { "command": "npx", "args": ["-y", "rea-agents@<version>", "mcp"] } } }
```

Pin one exact version. Then copy `.agents/skills/*` into the agent's skill folder and point its instructions file at this repo's `AGENTS.md`.

## Verifying

After setup, restart the agent and ask it to list MCP tools. REA's `binary_session`, `open_binary` and `analyze_function` should appear. `reentry doctor` says whether REA's registration passed its own checks (it runs `rea doctor --json` underneath) and whether the six skills are present at each destination.
