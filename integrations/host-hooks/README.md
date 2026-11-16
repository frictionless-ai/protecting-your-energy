# Additional local host hooks

The Cursor folder preserves the local knowledgebase context, evidence-reminder and validation-followup hooks, plus the prompt-uplift hook and its sibling deterministic prescreen module. These are opt-in host-specific adapters. Resolve their events against the target Cursor version before enabling them. They can emit `agent_message`, `additional_context` or `followup_message` according to their source workflow.

The Claude folder contains an optional PGE notifier. Configure `PYE_PGE_PLUGIN_ROOT` to an installed compatible PGE bridge. `PYE_PGE_OPEN_TERMINAL=1` opts into opening a macOS indicator window when the native tools exist. The notifier proceeds quietly when that bridge is unavailable. Its upstream attribution is retained with the PGE role notice in integrations/agents/claude.

The installed Herdr Claude hook and OpenCode plugin explicitly identify themselves as Herdr-managed. Keep those integrations with the Herdr installation and follow its update path. The inventory found no established local modification that justified bundling a separate copy. Compound Engineering's `ce-*` roles likewise remain dependency adapters.

Private Cursor hook state and generated caches remain in their original local state directories. The integration inventory retains hashes and source relationships. This directory does not change live hook configuration.
