# Thought Reconstruction engine

This component packages the existing Python library and stage engine, local canvas, thought-object schema and indexed reclamation skills.

Use the plugin's top-level thought-reconstruction command for dispatch. The source entry points remain available as `python3 bin/thought-reconstruction` for a configured library and `python3 bin/tr` for explicit pipeline stages.

## Configuration

Set `THOUGHT_RECONSTRUCTION_CONFIG` to a private JSON configuration outside the plugin and raw archive. The default is `$XDG_CONFIG_HOME/protecting-your-energy/thought-reconstruction.json`, with `~/.config` used when XDG_CONFIG_HOME is absent.

The configuration supplies `archive_root`, `output`, sources and optional reviews, repository research and semantic-processing settings. Paths resolve relative to that configuration file. Output and provider receipts must stay outside the raw archive. Replace these placeholder paths before use.

```json
{
  "archive_root": "/path/to/private/archive",
  "output": "/path/to/private/library",
  "reviews": "reviews.json",
  "sources": [
    {"kind": "jsonl", "path": "/path/to/private/owner-messages.jsonl", "project": "Example project"}
  ]
}
```

The source role `self` remains explicitly attributable input. Configure identity-based exports through `THOUGHT_RECONSTRUCTION_OWNER_ID` and `THOUGHT_RECONSTRUCTION_OWNER_ALIASES`. Aliases are a JSON array of owner names as they appear in curated Markdown headers. Both settings default empty, keeping personal identifiers outside the packaged code.

## Entry points

```sh
python3 bin/thought-reconstruction verify
python3 bin/thought-reconstruction query 'the idea to recover'
python3 bin/thought-reconstruction reclaim 'the idea to recover'
python3 bin/thought-reconstruction merge-plan
python3 bin/thought-reconstruction rebuild
```

The wrapper preserves `rebuild`, `verify`, `query`, `task`, `merge-plan`, `flag-report` and `reclaim`. Rebuild uses cached responses unless `--spend` is supplied. A provider-capable configuration and current authorization are required before explicitly enabling hosted processing.

The stage entry point uses `--repo-root` or `THOUGHT_RECONSTRUCTION_REPO_ROOT`. Its fallback looks for `y2/` above the current working directory. Set `THOUGHT_RECONSTRUCTION_ARCHIVE_ROOT` when using the stage CLI so its output checks include your raw archive's resolved location.

## Optional dependencies

Core parsing, grouping, ranking, validation and static canvas generation use Python's standard library. Versioned library publication uses POSIX file locking through `fcntl`.

Hosted paths use a separately installed Claude CLI with tool-disabled calls. Selected content leaves the machine when those paths are explicitly enabled. No model credential or provider configuration is bundled.

Repository research uses installed `rg` and `git`. Shared archive retrieval uses the plugin's `scripts/archive_access.py`, its configured retrieval backends and local model/index dependencies where required. An optional legacy semantic index uses its own configured Python environment and query script.

The reclaim helper configuration defaults to `$XDG_CONFIG_HOME/protecting-your-energy/config.json`. Override it with `PYE_ARCHIVE_ACCESS_CONFIG` or `--archive-access-config`. Helper paths accept `PYE_ARCHIVE_ACCESS_HELPER` and `PYE_ARCHIVE_DISPLAY_HELPER`. Display sanitization verifies its pinned helper digest, with `PYE_ARCHIVE_DISPLAY_SHA256` available for an explicitly configured replacement.

## Documentation

- [Reclamation workflow](docs/reclaim-workflow.md)
- [Library operations](docs/operations.md)
- [Implementation reference](docs/implementation-reference.md)
- [Component intent](INTENT.md)
- [Thought-object schema](schema/thought-object.schema.json)
- [Indexed reclamation skill](skills/thought-reconstruction/SKILL.md)

Private sources, generated libraries, model receipts, caches and original research artifacts stay in configured local locations. Packaging supplies the runtime source. Configured library, retrieval, provider and canvas outcomes still require verification in the installation where they are used.
