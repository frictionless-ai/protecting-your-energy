---
name: agentdecompile-server-env
description: "Use this skill when starting the AgentDecompile MCP server, setting GHIDRA_INSTALL_DIR, auto-match, auto-checkin, analysis-tier, or debugging session-id or proxy forwarding, including on Cursor Cloud."
license: AGPL-3.0-or-later
compatibility: Requires GHIDRA_INSTALL_DIR, Python 3.10+, Java 21, and uv
metadata:
  author: AgentDecompile
  version: "1.0"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# AgentDecompile server environment

Read AGENTS (`$PYE_AGENTDECOMPILE_ROOT/AGENTS.md`) for current operations,
USAGE (`$PYE_AGENTDECOMPILE_ROOT/USAGE.md`) for environment/session reference and
MCP security (`$PYE_AGENTDECOMPILE_ROOT/docs/MCP_CONFIGURATION_SECURITY.md`) for authentication.

Attach to the existing `http://127.0.0.1:8080/mcp`. The project plugin uses native
HTTP configuration and starts no proxy, JVM or dashboard. If a client requires
stdio, the existing `agentdecompile-proxy --transport stdio --backend-url
http://127.0.0.1:8080/mcp` with `AGENT_DECOMPILE_WEBUI_ENABLED=false` is the
compatibility option. Source: `src/agentdecompile_cli/server.py:proxy_main` and
`src/agentdecompile_cli/webui.py:launch_webui_sidecar`. Inspection is not a
successful client-connection claim.

Do not start another server, switch ports, clear sessions or restart services
during the current recovery mission. Diagnose an unavailable backend and report
the owner/blocker. No systemctl. Ghidra Server uses RMI/SSL; its credentials and
headers do not authenticate the MCP listener. Session IDs are not authentication.

Host MCP defaults come from the active host configuration. Local JVM setup requires the real Ghidra installation and Java
as documented in USAGE, but those generic startup recipes are reference-only here.
