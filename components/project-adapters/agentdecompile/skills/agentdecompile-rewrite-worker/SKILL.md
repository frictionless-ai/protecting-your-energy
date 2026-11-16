---
name: agentdecompile-rewrite-worker
description: "Use this skill when a recovery work_dir has pending rewrite-queue entries, or the user wants /loop rewrite fulfillment during an --autonomous campaign. Requires a work_dir."
license: AGPL-3.0-or-later
compatibility: Requires a recovery work_dir and the Agent/Task tool (no external LLM API)
metadata:
  author: AgentDecompile
  version: "1.0"
  argument-hint: "<work_dir>"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# agentdecompile-rewrite-worker

Read the [canonical project adapter](../../.agents/skills/agentdecompile-rewrite-worker/SKILL.md).

The [historical variant](LEGACY-INSTRUCTIONS.md) is retained for source comparison. Resolve current operations against the configured external project's authority before execution.
