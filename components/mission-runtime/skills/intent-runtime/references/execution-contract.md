# ExecutionContract

Compile this IR before any prose. Omit empty fields.

```
objective
requested_action          # answer | explain | diagnose | change | build | ...
deliverable
relevant_context
artifacts
previous_failures
hard_constraints
negations
authority_granted
authority_not_granted
response_contract
success_conditions
assumptions
unresolved_ambiguities
irreversible_or_external_actions
inferred_intent.direct_ask
inferred_intent.adjacent_impact
inferred_intent.recommended_cohesive_scope
inferred_intent.risks_if_partial
inferred_intent.expansion          # none | entailed
```

## Invariants

- **I1** — synthesized material only under `assumptions`
- **I2** — do not invent a motive
- **I3** — keep answer vs change. Flip is catastrophic
- **I4** — keep every negation and authority boundary
- **I5** — unbound and material → choose-and-note if reversible; ask only if the readings are different work

## Long-horizon one-liner

Stage `success_conditions`. Verify against tool results. Do not add
per-stage user check-ins.

## Inferred intent

Fill `inferred_intent.*` before dispatch. Any entailed expansion is also
recorded under `assumptions` as `[entailed]`.

## Privacy

Do not write the ExecutionContract to logs, telemetry, or files. Default telemetry
to lengths-only (`MISSIONRUNTIME_REDACT=1` or `redact_text: true`). Never
store raw user text to compensate for a missing hook.
