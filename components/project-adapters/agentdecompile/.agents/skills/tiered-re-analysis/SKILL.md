---
name: tiered-re-analysis
description: "Use this skill when starting reverse engineering, picking tools for a binary, or before open-project or decompile-function. Apply even if they only say look at this exe or what is in this binary, without naming Ghidra or tiers."
license: AGPL-3.0-or-later
metadata:
  author: AgentDecompile
  version: "1.0"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Tiered RE analysis

Read AGENTS (`$PYE_AGENTDECOMPILE_ROOT/AGENTS.md`) before operations and STRATEGY (`$PYE_AGENTDECOMPILE_ROOT/STRATEGY.md`)
for matcher order and acceptance. Use existing 8080 catalog actions for recovery.

| Tier | Use |
|---|---|
| 0 | Existing metadata, file triage, strings and static witnesses |
| 1 | Stored batch decompilation, BSim and export evidence |
| 2 | Read-only queries against existing analyzed Ghidra state |
| 3 | Missing deep analysis or authorized mutations after ownership checks |

Choose the cheapest sufficient evidence. First resolve program bindings and
stored analysis; an empty view or a false session flag alone does not justify
reanalysis. Reuse valid receipts, retain conflicts, and serialize shared writers.
These tiers classify tools; they do not reorder the corpus matcher or prove
recovery. Tool availability comes from the current advertised catalog.

Historical routing research (`$PYE_AGENTDECOMPILE_ROOT/docs/solutions/architecture-patterns/tiered-re-analysis-knowledgebase.md`)
is reference-only where its storage, confidence or operating rules differ.
