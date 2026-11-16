# Before and after

## Pairs that survived

| Bad | Good |
|-----|------|
| `Configuration persistence` | `Save settings` |
| `CLI entrypoint` | `Run from terminal` |
| `Test execution module` | `Run tests` |

The pattern: buttons and headings name an action the reader takes. They do not
name a part of the system.

## Slop patterns to catch

These three are recorded in `plain-ui-copy-core.md` as failure examples. The
original rewrites were lost, so rewrite them in context rather than copying a
fixed answer:

- `Guarded HTTP API, optional Web UI, native tray` — a comma-separated feature pile.
- `Enterprise-grade, AI-powered dashboard with real-time insights` — an adjective stack.
- `Unified observability console with granular telemetry aggregation` — stacked nouns plus buzzwords.

Each one says what the product *is*. Rewrite so it says what the user *does*,
one idea per sentence.

## Banned words

Buzzwords: seamless, robust, powerful, intuitive, cutting-edge, next-gen,
enterprise-grade, unified, granular, holistic, leverage, utilize.

Architecture tags that must never appear in UI copy: entrypoint, bridge, layer,
pipeline, orchestrator, native tray, whitelisted passthrough.

## Length limits

| Element | Limit |
|---------|-------|
| Headings | 6 words or fewer, verb or clear benefit |
| Subheads | 15 words or fewer, one idea |
| Card body | 1 sentence, practical value |
| CTAs | Verb + specific target |
