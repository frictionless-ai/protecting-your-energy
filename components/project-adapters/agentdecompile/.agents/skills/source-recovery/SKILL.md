---
name: source-recovery
description: "Use this skill when the user wants recovered C, objdiff, --dump-source, rematch, or reconstruct. Do not treat leftover target/ receipts as this run's source."
license: AGPL-3.0-or-later
metadata:
  author: AgentDecompile
  version: "1.0"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Source recovery

Read AGENTS.md (`$PYE_AGENTDECOMPILE_ROOT/AGENTS.md`) for operations and
STRATEGY.md (`$PYE_AGENTDECOMPILE_ROOT/STRATEGY.md`) for the single recovery policy.

Use the existing 8080 catalog. Inventory and corroborate existing analysis,
source and receipts before producing more; resume/import is valid for agents.
Never label reused artifacts as a fresh run. Regenerate only missing, invalid
or explicitly requested work. Terminal acceptance still requires the fresh
whole-image compiler/objdiff/relink checks in STRATEGY, with C+assembly-floor
and max-C variants separately accounted.

Corpus pipeline (`$PYE_AGENTDECOMPILE_ROOT/docs/CORPUS_PIPELINE.md`) and
critical-path reference (`$PYE_AGENTDECOMPILE_ROOT/docs/CRITICAL_PATH.md`) explain implementation.
Runtime reuse (`$PYE_AGENTDECOMPILE_ROOT/docs/RUNTIME_REUSE.md`) is a parallel branch and never
counts original-binary calls as recovered source. Follow AGENTS.md restrictions
on filesystem tests, systemctl, ports and duplicate compiler/Wine/Ghidra writers.
