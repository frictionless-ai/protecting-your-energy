# Plain Human Copy (anti–AI slop)

## Jurisdiction (vs voice-match)

| Surface | Owner |
|---------|-------|
| UI, landing, onboarding, i18n, marketing | **plain-ui-copy** (this file) |
| Internal docs, essays, code comments, work notes | **voice-match** skill |
| `docs/plans/*` with `artifact_contract` | **neither** — refuse rewrite |

On idiolect surfaces, suspend the comma-separated-noun-pile ban and the
one-adjective-per-sentence hard cap; use paragraph-level slop audit instead.

Applies to **all user-facing strings**: UI labels, landing pages, onboarding, toasts, empty states, marketing, in-app help. Code comments and internal notes are out of scope unless the user asks — use **voice-match** for those.

## The failure mode

Models compress feature lists into **adjective stacks** and **comma-separated noun piles** to sound concise. That reads like marketing filler, not human speech.

- Bad pattern: `"Guarded HTTP API, optional Web UI, native tray"`
- Bad pattern: `"Enterprise-grade, AI-powered dashboard with real-time insights"`
- Bad pattern: `"Unified observability console with granular telemetry aggregation"`

Fix: **one idea per sentence.** Say what the user **does**, not what the product **is**.

## Voice

- Plain spoken English. Short declarative sentences.
- Max **one** adjective per sentence (user-facing). Prefer zero.
- No buzzwords: seamless, robust, powerful, intuitive, cutting-edge, next-gen, enterprise-grade, unified, granular, holistic, leverage, utilize.
- No architecture tags as UI copy: entrypoint, bridge, layer, pipeline, orchestrator, native tray, whitelisted passthrough.
- Buttons: **verb + object** (`Save settings`, not `Configuration persistence`).

## Length

| Element | Limit |
|---------|-------|
| Headings | ≤ 6 words, verb or clear benefit |
| Subheads | ≤ 15 words, one idea |
| Card body | 1 sentence, practical value |
| CTAs | Verb + specific target |

## Before shipping copy

1. **Verb-first pass** — headings start with an imperative or name an action (`Run tests`, not `Test execution module`).
2. **Friend test** — rewrite as if explaining to a developer over coffee; ≤ 2 adjectives per paragraph.
3. **Slop audit** — flag sentences with 2+ adjectives, comma-separated feature lists, or stacked nouns; rewrite to subject–verb–object.

For before/after tables and audience-specific rules (UI vs public README), read `examples.md` and `audience-modes.md`. For bulk doc rewrites, use the `copy-rewriter` subagent.
