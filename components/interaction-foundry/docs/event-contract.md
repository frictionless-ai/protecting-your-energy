# Private ingestion contract v1

Adapters yield dictionaries, one per source record, into the ingestion store. This is an internal private contract, not the release case schema. Implementations and tests use synthetic fixtures; do not read or import original histories during implementation.

Every record has `position` (positive integer source ordinal), `status` (`accepted`, `excluded`, `quarantined`, `unsupported`), and `reason` (generic code, never source text). Accepted records additionally have `event`:

```
provider: nonempty string
conversation: nonempty string or null
native_id: nonempty string or null
identity_basis: native or artifact_position
kind: nonempty string
actor: object (role, optional id; no actor inference from quoted content)
timestamp: original string or null
parent_ids: list of source identifier strings
content: original string, list, object, or null
extra: object preserving other source fields and uncertainty
```

An accepted native identity requires provider + conversation + native_id. Otherwise identity is provisional and scoped to immutable artifact bytes + source position + provider. Never merge on message wording. Exact artifact copies share artifact identity, but private locators are observations. Content changes under an identical native identity create versions; import order does not select a current version. Discord reaction totals and export-dependent fields are observations, not additional interactions. Preserve all source facts privately; no raw fields in aggregate CLI output or exceptions.

Store interface: `ingest(path, adapter, database_path)` where `adapter(stream)` yields these records. The core hashes artifact bytes in bounded chunks, reopens UTF-8 input, consumes records incrementally, and stores an artifact transaction in SQLite. Reimport is idempotent. An iterator exception rolls back that artifact; invalid JSONL lines can yield quarantined records while later valid records survive. Retain per-record diagnostics and provenance. Return only aggregate status counts. The store is private caller-selected storage; CLI outputs must be constrained to ignored `private/` in the repo. Source files are read-only.

Adapter interfaces:

- `discord.iter_discord(stream)`: detect DiscordChatExporter envelope, iterate nested messages without unbounded reads. Require aware message timestamps and apply explicitly configured optional date bounds from the component README. Preserve references, authors, embeds, reactions and original ordering. Missing/naive dates are quarantined. Nonmatching envelopes are unsupported. Undated reactions retain unknown time attribution. Acceptance is ingestion eligibility, not a positive-social label or verified target identity. Linked replies alone do not prove praise or entertainment.
- `ai.iter_ai_jsonl(stream, provider=...)`: supported selector labels `claude_code_sessions`, `codex_sessions`, `cursor_transcripts`, `gemini_logs`. Parse each line with bounded size, dispatch source schemas, retain unknown types as explicit unsupported diagnostics. Preserve typed content, tool events, summaries, parent/sidechain data and original order. No Discord date filter. Session identity must come from source metadata when available; otherwise provisional artifact-position identity. Do not deduplicate summaries against response items without explicit identity evidence. Never infer failure, annoyance or stop cause from continuation wording.

No external dependencies. Bounded parsers must expose their record-size limit and diagnose oversize records. Streaming JSON envelope parser may live in discord.py and be reused later for graph/web adapters. ChatGPT/Claude web adapters, release extraction, semantic social labels and causal-stop classification are subsequent work, not claims of this initial slice. Keep archives, Cursor databases and secondary history adapters disabled.

Package files live in `src/interaction_foundry/`. Original source texts, account IDs and personal locators belong in private evidence storage. Source project tests remain outside this bundle. No model-effectiveness claims follow from bundling the implementation.
