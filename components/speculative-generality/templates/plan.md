# Speculative-generality work record

Use this as an output structure, not as a requirement to write a file. Fill only
with real task information; remove instructional text when delivering the record.

## Status and scope
Overall status; named batch; user objective; authorized paths; exclusions;
compatibility commitments; baseline revision/file state; relevant local changes.

## Observed facts and assumptions
Facts with inspected paths/ranges or supplied sources. Separate hypotheses,
unknown external API details, and user-required behavior.

## Future scenarios
| ID | Provenance | Possible future user/change/condition | Observable required behavior | Disposition and concrete reason |
| --- | --- | --- | --- | --- |

Use stable S1, S2, ... IDs. Do not relabel a hypothesis as a user requirement.
Disposition: ACCEPTED, COMBINED into a named scenario/capability, or OUT_OF_BATCH
with an explicit reason. Preserve unresolved or conflicting scenarios.

## Capability contracts
For each C1, C2, ...: scenario IDs; public contract; defaults/compatibility;
state/error/lifecycle semantics; planned implementation locations; dependencies;
verification route; cost and permission implications. Distinguish an implemented
extension mechanism from a not-yet-integrated future external service.

## Capability ledger
| Capability | Scenarios | Actual implementation locations | Evidence IDs or NOT_RUN | Status | Limitations / remaining work |
| --- | --- | --- | --- | --- | --- |

Before implementation, use NOT_IMPLEMENTED rather than one of the post-build
capability statuses. In a build report, use rules/verification.md statuses.

## Execution and inspection evidence
For E1, E2, ...: kind (EXECUTION/STATIC_INSPECTION/SUPPLIED); check; actual command
when applicable; cwd; revision/file state; exit code; result excerpt; limitations.
For an unrun check, say NOT_RUN and why. Never insert sample output as real output.

## Challenges and decisions
Findings by ID, accepted or disputed resolution, discriminating checks, unresolved
user choices. Preserve meaningful dissent. State why any proposed capability was
left out; absence of present demand cannot be the sole reason.

## Collaboration record
Actual roles invoked; independent initial inputs yes/no/unknown; advisory call count;
revision/repair count; skipped phases and why. A single-context fallback must be
named explicitly and must have user agreement.

## Remaining frontier
Futures outside this batch, concrete blockers, and the next decision needed. Do not
turn this section into a false assertion that all hypothetical needs were exhausted.
