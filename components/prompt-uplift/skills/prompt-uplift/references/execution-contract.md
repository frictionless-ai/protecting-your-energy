# ExecutionContract (intermediate representation)

Compile the message into this model-independent IR before writing any prose.
Rendering adapters change packaging, never semantics. Omit fields that are
empty; never pad.

```
ExecutionContract
  objective                      # what the user is trying to achieve (their words, resolved)
  requested_action               # answer | explain | diagnose | change | build | ... — verbatim mode
  deliverable                    # the artifact the user expects back
  relevant_context               # bound referents + environment facts from the session
  artifacts                      # typed, delimited payloads (logs, code, image descriptions)
  previous_failures              # neutral history of failed approaches, with why they failed
  hard_constraints               # task semantics: "no third-party modules", "8-bit encoding only"
  negations                      # every "don't/not/never/no", verbatim in meaning
  authority_granted              # what the executor may do without asking
  authority_not_granted          # explicit boundaries ("don't modify anything", "read-only")
  response_contract              # output shape: format, structure, required content, length priority
  success_conditions             # definition of done; staged for long-horizon work
  assumptions                    # everything the compiler synthesized rather than heard
  unresolved_ambiguities         # gaps the compiler could not close
  irreversible_or_external_actions  # flagged steps requiring pause-for-user
```

## Invariants

- **I1 — No invented requirements.** Synthesized material goes in
  `assumptions` (and assumption-marked `success_conditions`); nothing
  synthesized may masquerade as a user statement.
- **I2 — No manufactured motive.** If the user gave a reason, `objective`
  preserves it. If they said "fix this", resolve the referent and state the
  task — do not invent a business motivation. ("Give the reason" guidance
  applies when the reason is known; it does not license inventing one.)
- **I3 — Action-mode preservation.** `requested_action` is carried verbatim
  in mode. Turning "tell me how" into "make the change" (or vice versa) is a
  catastrophic failure.
- **I4 — Negation and authority preservation.** `negations`,
  `authority_granted`, and `authority_not_granted` survive into every
  rendering, verbatim in meaning.
- **I5 — Ambiguity honesty.** If `unresolved_ambiguities` is non-empty and
  materially affects the work, the contract tells the executor how to
  proceed: choose-and-note for reversible interpretations; ask the user only
  where readings diverge into materially different work.

## Long-horizon tasks (G7)

Stage `success_conditions` as milestones. Autonomy policy to render into the
executor prompt: internally verify milestones (ground progress claims in tool
results; prefer fresh-context verification for long runs); continue
autonomously through in-scope reversible work; pause only for destructive or
irreversible actions, real scope changes, or information only the user can
provide. Do not add per-stage user check-ins.

## Privacy

The contract embeds resolved user content by necessity. It lives in
conversation state only: never write it to logs, telemetry, or files, and
never quote it back to the user unprompted.
