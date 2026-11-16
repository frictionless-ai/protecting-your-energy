# Archive retrieval runtime

This component contains the reusable local query, role-qualification and original
capture-resolution helpers used by Protect Your Energy. Archives, derived tables,
indexes, models, private configuration and evaluation corpora remain external.

The optional dense-source closure is included as semantic_archive.py,
semantic_query_adapter.py, semantic_query_policy_adapter.py and
semantic_query_view.py. These preserve strict generation and source-policy
bindings. Existing generations require a reviewed compatible migration when
their bound code or policy changes. Bundling source alone does not migrate data.

`upar_retrieve.py` provides capabilities, search, SQL and tool routing without
starting an MCP server. Pass `--root` or set `UPAR_ROOT`. `query_sql.py` reads
configured Hive Parquet through in-memory DuckDB. The original-capture resolver
uses bounded reads, version checks, configured source roots and package integrity
pins. Its result describes examined captures and remaining gaps.

## Dependencies

The query runtime requires Python, DuckDB, PyArrow and NumPy for the complete
Parquet and hybrid paths. The lightweight help and capability paths defer heavy
imports. `sentence-transformers` is optional for the source hybrid implementation's
dense encoder and cross-encoder. LanceDB is optional for the source helper's
vector-store path. Configured models and vector data remain external.

The primary root `scripts/semantic_retrieve_portable.py` uses a local ONNX encoder and
requires NumPy, onnxruntime and tokenizers plus compatible external model files.
It sets offline inference flags and rejects Python network connections when
executing its commands. No model or provider was invoked during packaging.

`scripts/semantic_retrieve.py` retains its exact tracked source bytes for existing
generations and external adapters whose integrity pins bind that source. Bundled
backends and new primary routes use the portable entry. A reviewed generation
migration is required before switching an existing bound index to changed code.

## Private policy

`PYE_ARCHIVE_POLICY_FILE` selects a private JSON policy. The default location is
`${XDG_CONFIG_HOME:-~/.config}/protecting-your-energy/archive-policy.json`.

```json
{
  "owner_discord_id": "",
  "owner_aliases": [],
  "excluded_author_ids": [],
  "excluded_name_hashes": [],
  "allowed_source_roots": [],
  "archive_root": "",
  "notes_account_rule": ""
}
```

Owner aliases are case folded. Excluded names are represented by SHA-256 hashes
of stripped, lowercased names. Source roots must be absolute. The capture resolver
permits home sources and the configured roots while retaining its path guards
and no-symlink traversal. Extra policy keys remain available to the enclosing
package. Missing default policy leaves identity unconfigured. An explicitly
selected missing policy or malformed present policy produces an error.

`THOUGHT_RECONSTRUCTION_OWNER_ID` and JSON-array
`THOUGHT_RECONSTRUCTION_OWNER_ALIASES` override owner identity when supplied.
Private identity and exclusion values are loaded at runtime.

`notes_account_rule` retains a known importer's account-attribution label so the
read-only policy adapter can keep account-owned Notes in the context-document
lane. `PYE_NOTES_ACCOUNT_RULE` can override it. The saved label establishes
neither authorship nor adoption.

## Package and legacy routing

Root helpers prefer `PYE_RETRIEVAL_TOOLING` when configured, then this bundled
directory, then the earlier local helper directory when the component is absent.
The capture resolver reads common/helper source pins from the package's
`assets/module-integrity.json`. Root integration must refresh that manifest after
source changes. An explicitly configured legacy helper remains governed by its
recorded source pin or explicit override.

The copied query connector preserves an existing persistent DuckDB artifact when
called in read-only mode. Builder operations remain explicit commands. The MCP
primitive source retains an explicit append-memory operation for existing callers.
Reconstruction acquisition uses the read paths and preserves archive originals.
