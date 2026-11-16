# Local agent integrations

These files preserve local role prompts and native profiles for use with the host that supports them.

| Folder | Content |
| --- | --- |
| `shared/` | Local worker tiers, memory maintenance, copy rewriting and independent review roles. |
| `claude/` | Planner, generator, PGE orchestrator and evaluator variants in Claude agent format. |
| `cursor/` | History search, archive refresh, form assistance, runner builds and related local roles. |
| `codex/` | Native TOML role profiles, including host-specific model settings where present. |
| `scripts/` | Read-only prompt-history search and an optional recovery-prompt extraction helper. |

The package's top-level agent routes determine which profiles the host exposes. These copies do not edit installed agent directories or enable model providers.

## Configuration and dependencies

Set `PYE_PLUGIN_ROOT` to the installed checkout for script commands in the history-search role. `search-prompt-history.py` uses local history stores under the current home directory and honors `CODEX_HOME`. It reads histories and SQLite databases locally. Its output can contain private prompts and should remain inside the authorized task.

`extract-re-prompts.py` keeps the original recovery-related selection pattern. It writes its derived output to a private application-data directory by default. `PYE_HISTORY_OUTPUT` can select another authorized destination. Invoke it only when that recovery-history extraction is requested.

`archive-updater` uses `PYE_ARCHIVE_ROOT` or the destination recovered from the current task. It preserves original capture and inbox boundaries. The local source role's earlier machine-specific name is retained only in the private provenance map.

`form-assist` reads a configured private profile through `FORM_ASSIST_PROFILE`, with a default under `~/.config/form-assist/`. Medical, financial, contact, browser-profile and credential-export facts from the original local role have been removed. The template retains source-backed form entry, masked-field checks, privacy, accessibility and scoped authorization behavior.

The copy-rewriter references the user's installed plain-copy guidance. The shared integration includes the general copy rule. Some local agent procedures also require their named tools, model access, browser capabilities, specialist skills or CLI executables. Recover these prerequisites from the active host and follow current user permissions.

PGE and evaluator prompts preserve their original host tool lists and workflows. Those tool names are capabilities to resolve in a compatible host. Bundling a prompt does not establish live browser testing, model execution or pipeline completion.

## Provenance and privacy

The PGE role family is explicitly vendored from orion-gz/Claude-Trinity2.7.0 under its manifest-declared MIT license. The [upstream notice](claude/UPSTREAM-NOTICE.md) records attribution and the available license declaration. Related Codex profiles are native-host adaptations. Other local prompt directories supplied no separate license file for their individual variants. The private integration inventory records exact source paths and hashes, and the originals remain preserved.

Third-party Compound Engineering agent adapters and Herdr integrations remain documented dependencies. Private profiles, histories, local state and backup prompts are outside this source bundle.
