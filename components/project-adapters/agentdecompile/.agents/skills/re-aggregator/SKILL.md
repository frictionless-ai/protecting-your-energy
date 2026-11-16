---
name: re-aggregator
description: "Use this skill when asked to merge several function analyses, resolve disagreements, or report RE consensus and remaining gaps."
license: AGPL-3.0-or-later
metadata:
  author: AgentDecompile
  version: "1.0"
  role: aggregator
  argument-hint: "Batch of function artifacts, or all"
---

This optional adapter uses the external checkout selected by `PYE_AGENTDECOMPILE_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# RE Aggregator

Read AGENTS (`$PYE_AGENTDECOMPILE_ROOT/AGENTS.md`), STRATEGY (`$PYE_AGENTDECOMPILE_ROOT/STRATEGY.md`) and the
artifact protocol (`$PYE_AGENTDECOMPILE_ROOT/.github/instructions/re-artifact-protocol.instructions.md`).
Merge findings for the same fingerprint-bound instance or supported logical
identity. Never merge solely because addresses or confidence scores agree.

Preserve evidence and provenance per field. Prefer stronger supported names over
placeholders, retain conflicting types and ABI/layout witnesses, deduplicate
xref facts, and keep unresolved gaps explicit. A consensus score is advisory,
not proof or automatic mutation authority.

Return merged artifacts with source/review locators, field decisions, unresolved
conflicts, bounded analysis convergence and proposed actions. Do not apply them
unless authorized; field-level propagation, source compilation and per-build
verification gates remain in STRATEGY. Reassign gaps within task and resource
limits. Agreement among workers never substitutes for external evidence.
