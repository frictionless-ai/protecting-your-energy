# Components

## Core

| Component | Bundled source | Public routes |
| --- | --- | --- |
| Thought reconstruction | `components/thought-reconstruction/` | `skills/thought-reconstruction`, `scripts/thought_reconstruction.py` |
| Intent runtime | `components/intent-runtime/` | `skills/intent-runtime`, `skills/distill-intent`, specialist roles in `agents/` |
| Prompt uplift | `components/prompt-uplift/` | `skills/prompt-uplift` |
| Prompt-submit guidance | `components/semantic-expression/hooks/intent_coach.py` | `hooks/energy.py`, Claude and Codex submit-hook registrations |

The umbrella skills `protecting-your-energy` and `protect-your-energy` select
among these capabilities. Relative skill and agent links resolve to the bundled
source. Component licenses and source attribution remain with their components.

The submit hook originated as per-message intent and technical-phrasing coaching.
The bundled version asks for context recovery and preservation of the request.
It provides rewritten prompts or phrasing coaching when requested. It returns
`hookSpecificOutput.additionalContext` and runs without a provider or transcript
logging. [Hook behavior](components/semantic-expression/README.md)

## Reconstruction dependencies

These support thought reconstruction's existing commands.

- `components/thought-reconstruction-engine/` supplies the indexed library,
  reclamation, schema and local canvas. The `reclaim` skill exposes its workflow.
  [Engine guide](components/thought-reconstruction-engine/README.md)
- `components/archive-retrieval/` supplies original-source resolution and optional
  indexed retrieval backends used by `scripts/archive_access.py` and the engine.
  [Archive access](references/archive-access.md)
- `scripts/archive_display.py` sanitizes derived display payloads.
  `scripts/note_capture_reader.py` resolves original Notes exports during hydration.
- `scripts/semantic_retrieve_portable.py` supports configured local dense retrieval.
  `scripts/semantic_retrieve.py` preserves the bytes pinned by existing generations.
  [Dense retrieval](references/semantic-retrieval.md)
- `assets/module-integrity.json` records module hashes checked by helper loaders.
  After reviewing a source change, refresh with
  `python3 scripts/refresh_module_integrity.py --write`. Omit `--write` to check.

The dispatcher reads optional archive identity configuration from
`${XDG_CONFIG_HOME:-~/.config}/protecting-your-energy/archive-policy.json`.
`PYE_ARCHIVE_POLICY_FILE` selects another file. Explicit environment variables
retain precedence. The engine uses `THOUGHT_RECONSTRUCTION_CONFIG`; archive
access uses `PYE_ARCHIVE_ACCESS_CONFIG`. Their guides describe the schemas.

## Scope

This package contains context recovery, intent compilation, prompt preparation
and the submit hook, together with their implementation dependencies.

General workflow orchestration, energy scoring, opportunity scanning, background
mission supervision, generic worker packs, independent software reconstruction,
reverse-engineering adapters, token advice, unrelated writing skills and project
adapters have been removed from the package. Earlier versions remain available
in Git history.

Intent runtime retains its own task and mission procedures, compilation helpers,
specialist prompts and optional telemetry adapters. These belong to that core
component. Nested hook templates require deliberate setup. Telemetry defaults
off. [Intent runtime guide](components/intent-runtime/README.md)
