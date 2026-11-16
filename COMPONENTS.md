# Included components

The plugin exposes its skills through `skills/`, command procedures through
`commands/` and agent entry points through `agents/`. Component source stays
under `components/` so its internal imports and references resolve together.

The [itemized catalog](assets/component-catalog.json) lists direct skill, agent
and command entry points alongside component-specific source variants, host
profiles and hook configurations.

| Component | Included behavior | Source location |
| --- | --- | --- |
| Energy workflows | Momentum, continuity, recurring friction, choosing work and evaluation | `skills/`, `scripts/`, `references/` |
| Thought reconstruction | Local discovery, Roust-assisted acquisition, contextual inspection and curated document assembly | `components/thought-reconstruction/` |
| Reconstruction library | Existing reclaim, rebuild, query, verification and task commands | `components/thought-reconstruction-engine/` |
| Intent runtime | Context recovery, scoped execution guidance and intent distillation | `components/intent-runtime/` |
| Interaction foundry | Local interaction curation and context extraction | `components/interaction-foundry/` |
| Semantic expression | Coherent expression and context-aware replies | `components/semantic-expression/` |
| Prompt uplift | Preparing an execution prompt for a target executor when context needs to travel | `components/prompt-uplift/` |
| Independent reconstruction | Behavioral observation, specification, separated implementation roles and conformance workflows | `components/independent-reconstruction/` |
| Local expression and intent skills | Intent recovery, plain copy, voice-aware writing and meaning-preserving editing | `components/local-skills/` |
| Archive retrieval helpers | Original-source resolution, indexed lookup and configured local retrieval | `components/archive-retrieval/` |
| Token guide | Quiet, advisory hints about repeated tool calls, waiting, output volume and session cost | `components/token-guide/` |

## Optional component workflows

The source bundle also retains separately scoped workflows. Their skills,
agents and hook configurations stay together inside the component. Select a
component through the host's explicit local plugin-loading mechanism when its
workflow applies. The root hook composition leaves these registrations inactive.

| Component | Included workflow | Guide |
| --- | --- | --- |
| Goal loop | Project-local goals with configured shell verification and stop-hook continuation | [Integration](components/goal-loop/INTEGRATION.md) |
| From evidence | Evidence aggregation, mindset distillation and generation of skills, agents, rules and hooks | [Integration](components/from-evidence/INTEGRATION.md) |
| Speculative generality | Requested future-capability planning, building and review | [Integration](components/speculative-generality/INTEGRATION.md) |
| Mission runtime | Retained mission, prompt and intent workflows, with optional local telemetry | [Source guide](components/mission-runtime/README.md) |
| Re-entry | Reverse-engineering observation, recovery, matching, verification and export procedures | [Integration](components/re-entry/INTEGRATION.md) |
| Codex better subagents | Source worker roles, model routing and explicit host configuration | [Source guide](components/codex-better-subagents/README.md) |
| Project adapters | Retained project-local skills, roles and helper instructions with external product dependencies | [Adapter index](components/project-adapters/INDEX.md) |

Each component retains its source notices and applicable license terms. The
component guides identify required runtimes, external services and inherited
implementation limits.

## Commands

Run the package entry points from this repository or use their absolute paths.

```sh
python3 scripts/thought_reconstruction.py --help
python3 scripts/thought_reconstruction.py discover --help
python3 scripts/thought_reconstruction.py reclaim --help
python3 scripts/ir.py --help
```

The reconstruction dispatcher includes both the acquisition adapter and the
older library interface. Its command guide describes private configuration,
optional Roust and library dependencies. [Reconstruction guide](scripts/thought-reconstruction/USAGE.md)

## Agents and host adapters

Portable role prompts and host-specific profiles are included under
`integrations/agents/`. The host directories preserve the formats used by Codex,
Claude and Cursor. Personal facts and voice banks are configured locally.
[Agent adapters](integrations/agents/README.md)

The main prompt hook composes recovery guidance and task continuity. Scoped
archive guards support comprehensive reconstruction. Shared adapters include
examples for Claude, Codex, Cursor, Gemini and OpenCode. Independent
Reconstruction's own hooks remain project-scoped through its component.
[Shared hooks](integrations/shared/README.md)

Claude's root hook configuration also forwards tool failures and automatic-mode
permission denials to the advisory guide. Denial events record context for a
later suggestion while preserving the host's decision. Codex uses its separate
event configuration. [Claude hook reference](https://code.claude.com/docs/en/hooks)

## Configuration and external sources

Archive locations, owner identity, exclusions, private profiles, indexes, models
and credentials belong in local configuration. The reconstruction dispatcher
can read the private archive policy at
`${XDG_CONFIG_HOME:-~/.config}/protecting-your-energy/archive-policy.json`.
Environment variables retain precedence. Existing private legacy configuration
is supported by the relevant adapters.

The original `scripts/semantic_retrieve.py` is retained byte-for-byte for
existing generations whose policy records pin its source. New portable dense
configuration uses `scripts/semantic_retrieve_portable.py`. Generation migration
requires reviewing the recorded policy and source compatibility.

Local dense retrieval requires its Python dependencies and a configured model
and index. Roust is optional and the acquisition scanner remains available when
it cannot run. The individual components document their requirements.

External installed skill packs retain their upstream sources and licenses.
The dependency catalog records source URLs, skill names and recorded content
hashes from the local installation registry. [External skill sources](assets/external-skills.json)

Historical evaluation runs, personal evidence, credentials, generated indexes,
private voice profiles and runtime state remain in local working locations.
The integration's private source mapping records source hashes, adaptations and
omissions for review.

## Maintaining bundled helpers

Several helper loaders verify sibling module bytes before executing them.
Their reviewed hashes live in `assets/module-integrity.json`, avoiding circular
source-file pins. After reviewing a source change, update this package metadata
with `python3 scripts/refresh_module_integrity.py --write`. Running the command
without `--write` checks the current metadata.
