# Verification of future capability

## Contract before verdict

For each accepted capability, specify the consumer-visible operation, inputs and
outputs, state/lifecycle, failure semantics, and compatibility obligations relevant
to its future scenario. A promise must be specific enough that a counterexample
could refute it. Do not convert uncertainty about demand into uncertainty about
what the implemented interface promises.

Use these checks where relevant, not as a ritual requirement for every feature:

| Claim | Discriminating evidence |
| --- | --- |
| A backend is interchangeable | An independently written consumer or test implementation exercises the public seam without editing the core dispatch path. |
| A policy is configurable | Two supported settings produce the intended different behavior; an invalid setting fails explicitly. |
| Data can evolve | An older representative payload remains readable, and unsupported/newer data is handled according to a declared policy. |
| Failure/retry handling is extensible | Deterministic injected failures exercise retry limits, cancellation and idempotency rules without real spending or damage. |
| A lifecycle is reusable | Setup/teardown and repeated use obey the contract, including failed setup where relevant. |
| Concurrency is supported | A deterministic interleaving or suitable stress check exercises the actual shared-state contract. |
| An integration works | The relevant real integration was exercised. Local substitution alone proves only local behavior and the seam. |

A test implementation does not need to duplicate the production implementation.
It should deliberately vary something the proposed abstraction promises to tolerate.
For example, vary iteration order or error timing when the contract permits it.
Do not introduce a second production backend merely to legitimize the first one's
interface; prospective need already legitimizes the interface in this workflow.

## Evidence records

For each check, record an evidence ID, the actual command or observation, working
directory, tested revision/file state, exit code when executed, result excerpt,
and any excluded environment or limitation. Redact secrets. If a command was not
executed, explicitly mark NOT_RUN and record why. Logs supplied by a user are
SUPPLIED evidence; label them rather than presenting them as your own tool run.

Distinguish EXECUTION (observed run), STATIC_INSPECTION (source-based inference),
and SUPPLIED (provided by someone else). A source review cannot demonstrate runtime
success. Existing passing tests do not establish a new capability unless they
exercise its contract. Stale logs from before a repair cannot verify the repair.

Capability status is one of VERIFIED, IMPLEMENTED_UNVERIFIED, BLOCKED, or DEFERRED.
VERIFIED means the stated scope of the contract has matching evidence; it does not
mean universally correct. DEFERRED requires a named scope, budget, or user decision;
"no one needs it today" is not an acceptable reason. Any accepted capability in
another state prevents an overall COMPLETE verdict.

## Challenger finding format

For each finding return:

    Finding ID / scenario and capability ID
    Category: CONTRACT_GAP | MISSING_CAPABILITY | FAKE_GENERALITY |
              REGRESSION | SECURITY | EVIDENCE_GAP | AUTHORITY_CONFLICT
    Location: actual path and relevant lines, or the plan clause
    Counterexample: concrete condition that violates the claim
    Evidence: inspected source or execution record; otherwise a labeled hypothesis
    Discriminating check: smallest useful test or observation
    Required change: preserve intended capability while fixing the defect
    Blocking: yes/no, with a reason tied to an accepted contract or user constraint

Avoid purely aesthetic objections and ungrounded praise. Identify no findings when
none are supported, but keep NOT_RUN checks and evidence gaps visible. Agreement
between agents does not resolve a failing check.

## Example of sufficient scope labeling

Claim: callers can supply a custom storage implementation without editing the
repository's core. Evidence: production local adapter passes its tests and a small
independently written adapter is accepted through the documented injection point.

This can verify substitution. It does NOT verify a cloud vendor, crash durability,
transactions, encryption, or cross-process consistency unless those contracts and
checks were separately implemented. Report the narrower truth without deleting
the abstraction or pretending that all anticipated integrations now exist.
