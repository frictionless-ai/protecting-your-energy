# Optional project adapters

These project-specific skills, role prompts and small helper scripts stay nested. Select the adapter for the actual task and inspect the current external project's instructions before acting. Commands and source-file paths in an adapter refer to that configured project checkout unless they explicitly link a bundled reference. Root plugin skill discovery and hooks are unchanged.

## Project roots and dependencies

| Project | Bundled entry | Private configuration and external dependencies |
|---|---|---|
| AgentDecompile | [Canonical skills](agentdecompile/.agents/skills/) and [Copilot loaders](agentdecompile/.github/agents/) | Set `PYE_AGENTDECOMPILE_ROOT` to the active checkout. Its current AGENTS.md, STRATEGY.md, advertised action catalog, corpus, Ghidra analysis, compiler and objdiff remain external. Source snapshot expects the existing local workbench. Corroborate actual serving ownership and configuration. |
| ModSync | [Canonical skills](modsync/.agents/skills/) and [role prompts](modsync/.claude/agents/) | Set `PYE_MODSYNC_ROOT` to the active checkout. .NET, patcher engines, game installations, download store, mod-builds and runbooks remain external. Configure `MODSYNC_HOT_ROOT` and `MODSYNC_ARCHIVE_ROOT` before using path examples. Legacy folder-name variants are retained under `legacy-variants` as reference instructions. |
| ModSync design system | [Design instruction](modsync-design-system/skills/modsync-design/SKILL.md) | `PYE_MODSYNC_DESIGN_ROOT` supplies the external design kit, README, tokens, styles, brand assets and components. |
| ModSync design project variant | [Design instruction](modsync-design-project/skills/modsync-design/SKILL.md) | `PYE_MODSYNC_DESIGN_PROJECT_ROOT` supplies this distinct external project's design artifacts. Both instruction variants are retained. No generated design artifacts or product UI data are bundled. |
| kq | [Query](kq/skills/kq-query/SKILL.md) and [formats](kq/skills/kq-formats/SKILL.md) | `PYE_KQ_ROOT` identifies the source checkout when needed. Runtime `kq` and authorized game/resource input remain external. Existing `KQ_INSTALL` or CLI options select the target. |
| PyKotor | [Assembly/transpilation parity](pykotor/skills/assembly-transpile-parity/SKILL.md) | `PYE_PYKOTOR_ROOT`, the external project, binary evidence and configured analysis tools. Similarity between two generated implementations still requires independent comparison with the original evidence. |
| KPatcher | [Managed NSS/NCS integration](kpatcher/skills/lfg/SKILL.md) | `PYE_KPATCHER_ROOT` and optional `PYE_ANDASTRA_ROOT` identify external source references. .NET, DeNCS sources and current project instructions remain external. Existing manual invocation restriction is preserved. |
| clifwrap | [Browser authentication](clifwrap/.agents/skills/clifwrap-browser-auth/SKILL.md) and [role](clifwrap/.agents/agents/clifwrap-browser-auth.md) | `PYE_CLIFWRAP_ROOT` supplies product auth scripts and CLI. Private browser-auth configuration, browser profiles, Patchright and vault backend remain external. The small bundled vault bridge accepts `CLIFWRAP_VAULT_SESSION_FILE`, `CLIFWRAP_VAULT_BIN` and `CLIFWRAP_VAULT_SESSION`. Its fallback session-file path follows XDG state. |
| Community bots | [Cloud development](community-bots/skills/cloud-agent-run-test/SKILL.md) | `PYE_COMMUNITY_BOTS_ROOT`, source workspace, Node/pnpm, configured services and private credentials. The local adapter references Trask and pazaak workflows. |
| ChangeEdit | [INI specification](changeedit/.github/skills/changes-ini-spec/SKILL.md) and [Delphi form scaffolding](changeedit/.github/skills/delphi7-form-scaffold/SKILL.md) | `PYE_CHANGEEDIT_ROOT` supplies Pascal/DFM sources and current project conventions. Both adapters retain manual-only invocation. |
| token-guide | [Run and audit instructions](token-guide/skills/run-token-guide/SKILL.md) | `PYE_TOKEN_GUIDE_ROOT` supplies the product hook and audit CLI. Provide an explicitly authorized private transcript for replay. Original smoke fixtures and their runner stay in the external source project. |

The root names above are a configuration convention for the agent selecting an external checkout. This bundle does not install repositories or automatically resolve those environment values. Read the configured root directly. An unset root or missing dependency is an explicit gap to resolve from current context.

## Source variants and operation boundaries

AgentDecompile's `.agents/skills` bodies are the canonical procedure. Its human-facing skill loaders remain linked to those bodies. Two differing generic historical bodies are preserved in `LEGACY-INSTRUCTIONS.md` beside their loaders. ModSync's deprecated underscore-named entry and distinct older project variants are also reference-only files. Historical instructions do not override current project authority or user constraints.

Validation recipes describe the original project workflows. They supply no new authorization to run tests, mutate installations, start services, contact providers, install hosts, or publish. This bundle includes no corpus, transcript, credentials, model artifacts, game tree, fixture cases or evaluation results.

## Attribution and license boundaries

Original author/frontmatter attribution is preserved. Each copied license remains within its project directory. AgentDecompile declares AGPL-3.0-or-later, ModSync declares BSL-1.1, kq and clifwrap include MIT license texts, and KPatcher includes LGPL-3.0 text. These nested terms remain applicable to their source.

PyKotor metadata declares LGPL-3.0-or-later, while its adapter source has no separate license text at the inspected project root. No standalone grant was located for the two ModSync design instructions, ChangeEdit adapters, Community Bots adapter or token-guide adapter. Their source attribution and this uncertainty are retained for review. The parent plugin's license does not replace these project-specific terms.

Upstream web-design-guidelines, third-party UI skill packs, GPT Researcher's upstream developer skill, vendor/cache duplicates and worktree exports remain external dependencies. The private integration inventory records the selected originals, hashes, excluded duplicates, and unresolved sources.
