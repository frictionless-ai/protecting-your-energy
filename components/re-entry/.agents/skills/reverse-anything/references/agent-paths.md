# Agent paths

For manual repair when `reentry setup` cannot run. REA owns MCP registration; these are the destinations it and re-entry write.

## MCP server block

```json
{ "mcpServers": { "rea": { "command": "npx", "args": ["-y", "rea-agents@<version>", "mcp"] } } }
```

Pin one exact version. Codex uses the TOML form `[mcp_servers.rea]` with `command` and `args`; OpenCode uses `mcp.rea` or its V2 `mcp.servers` table; Zed uses `context_servers`.

## Where skills go

| Agent | Skills folder |
|---|---|
| Claude Code | `~/.claude/skills/` or `$CLAUDE_CONFIG_DIR/skills` |
| Gemini CLI | `.agents/skills` under its home |
| Codex, Cursor, OpenCode, Copilot CLI, Qwen Code, Grok Build | `~/.agents/skills/` |

Copy all six re-entry skill folders together. `re-match`, `re-observe`, `re-recover`, `re-verify` and `re-export` assume `reverse-anything/references/rules.md` is a sibling.

## Pointer files

- Cursor: `.cursor/rules/reverse-anything.mdc` in the project, pointing at `AGENTS.md`.
- Claude Code and Gemini CLI: `CLAUDE.md` and `GEMINI.md` as one-line pointers at `AGENTS.md`.
- Codex, OpenCode, Copilot: read `AGENTS.md` natively.

## Verifying

Restart the agent. Ask it to list MCP tools: `binary_session`, `open_binary`, `analyze_function` are REA's. Ask it to list skills: the six re-entry names should appear. `rea doctor --client <id> --json` reports REA's own view of the registration.
