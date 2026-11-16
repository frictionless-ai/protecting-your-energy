# Interaction Foundry

Curate authorized interaction events into source-linked candidate lessons,
reviewed generalized cases and scoped advisory context. This component includes
the local ingestion, provenance, registry, context and handoff implementation.

Source files stay separate from private derived material. Every scan takes an
explicit source directory and output location. Use a private output directory
outside the source tree. Account attribution requires an explicit private
identity attestation. Candidate signals need contextual review before they can
establish a lesson or an outcome.

## Running the component

Python 3.11 or newer is required. From this directory, modules can run directly
with `PYTHONPATH=src python3 -m interaction_foundry.<module>`. The `scan`,
`contract_scan`, `upar_scan`, `upar_extract`, `analyze`, `lineage`, `friction`
and `social` modules expose command-line interfaces. Use `--help` to inspect
their input formats and required paths before processing authorized data.

Installing this component with `python3 -m pip install .` provides the
`interaction-foundry-hook` command. The hook requires `--registry` and a
host-neutral JSON request on stdin containing a `task_id`. It opens the registry
read-only and returns supplemental context. A host adapter must deliberately
map that envelope into its hook protocol. This component does not automatically
register a host hook or activate learned rules.

Core runtime dependencies are Python's standard library and a system timezone
database. UPAR source serialization uses POSIX `fcntl` when available and a
process-local lock on other platforms. The optional `hub` dependency enables
explicit reviewed dataset publication workflows. No upload occurs at import.

## Source selection

Original-format scans expect family subdirectories named `discord`,
`claude_code`, `codex_cli`, `cursor_agent`, `chatgpt_export` and
`claude_ai_export`. UPAR scans accept an explicit normalized records directory.
Unsupported formats, parser failures and configured bounds remain reportable
coverage gaps. Lexical friction signals select candidates for review.

Discord period screening accepts all valid timezone-aware timestamps by
default. Set `INTERACTION_FOUNDRY_DISCORD_START` and
`INTERACTION_FOUNDRY_DISCORD_END` to ISO dates for an inclusive lower and
exclusive upper bound. `INTERACTION_FOUNDRY_DISCORD_TIMEZONE` selects an IANA
timezone, defaulting to UTC. These settings apply to the scan and social
screening helpers that call `discord_in_period`.

## Curation and contracts

The [curation skill](skills/curate-interactions/SKILL.md) describes evidence,
attribution, scope and review. See the [event contract](docs/event-contract.md),
[dataset contract](docs/dataset-contract.md),
[identity format](docs/discord-account-attribution.md),
[extraction prompt](docs/prompts/repair-extractor.md) and
[privacy research](docs/research/privacy-and-evaluation.md).

The [strategy](docs/STRATEGY.md) retains proposed evaluation criteria from the
source project. Those criteria describe intended evaluation. Bundling this
component does not establish model effectiveness, archive coverage or a
verified user benefit. Private source material, historical operational reports,
release machinery in the source project's separate `mod` package and its
existing tests remain outside this bundle.
