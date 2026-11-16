---
name: mcp-debugging
description: "Use this skill when MCP calls time out, tools are missing, schemas mismatch, or the user mentions MCP Inspector, mcptools, mcp-debug, mcp-trace, FastMCP, sandbox, or GUI/coord failures."
license: AGPL-3.0-or-later
metadata:
  author: AgentDecompile
  version: "1.0"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# MCP debugging

Read AGENTS (`$PYE_AGENTDECOMPILE_ROOT/AGENTS.md`) and [server environment](../agentdecompile-server-env/SKILL.md).
Diagnose the existing 8080 backend without restarting it or switching ports.

Check the configured endpoint/transport, advertised tool schema, session ID,
selected project/binary, authentication boundary, and existing logs. Distinguish
a missing program binding from missing analysis. Corroborate process ownership
before proposing any operational change; a timeout alone does not establish death.
Never retry a mutation blindly after an uncertain response.

The project plugin connects directly to existing 8080 over native HTTP.
Host MCP defaults come from the active host configuration. Historical debug recipes under `references/` are
implementation references, not permission to start, reconnect, mutate or replace
the current recovery environment.
