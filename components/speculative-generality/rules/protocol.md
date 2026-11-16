# Coordinator protocol

The main session is the coordinator and sole implementer. The three plugin agents
are distinct read-only collaborators, not three simulated titles in one response.
Use the host's actual agent dispatch facility and the named custom agent type,
not a generic conversation fork, so the role's prompt and read-only tool definition
apply. A supported follow-up mechanism may
resume an agent; otherwise launch a fresh context with the relevant handoff packet.
Do not invent tool names, simulate tool results, or claim separate agents ran when
no dispatch occurred.

Read `rules/policy.md`, `rules/verification.md`, and `templates/handoff.md` from the
plugin root before acting. Read `templates/plan.md` when producing a plan. Research
and evaluation documents are reference material, not mandatory runtime context.

## 0. Establish the brief

Capture the user's objective, authorized paths/changes, compatibility promises,
explicit exclusions, known resource limits, and the current task mode. Inspect
relevant source and project guidance before claiming facts. Record the baseline
revision or starting file state and known local modifications. Do not infer a
clean worktree or run a cleanup command. In read-only modes use file-reading tools;
a supplied revision/diff is useful but not required to inspect known files.

Modes:
- PLAN: inspect and return a plan; no commands, edits, or saved report files.
- BUILD: implement and verify the declared batch with normal host permissions.
- REVIEW: inspect and return findings; no commands or edits. Supplied execution
  logs may be assessed, but unrun tests remain unverified.

If the brief or target is genuinely missing, ask one focused question. Otherwise
state a reasonable interpretation and proceed. Questions about paid services,
incompatible public APIs, destructive migration, or policy conflicts are substantive
approval boundaries, not invitations to ask approval for every ordinary edit.

## 1. Independent discovery

Dispatch `speculative-generality:future-scout` and
`speculative-generality:extension-architect` with the same brief and repository
facts, but WITHOUT either agent's initial proposal. Their objectives differ:
the scout generates future scenarios; the architect independently identifies
change barriers and candidate contracts. Parallel execution is optional; separate
initial inputs matter more than simultaneous execution. If the host exposes more
shared context than intended, disclose that independence was not established.

Usually a few well-specified scenarios are more useful than dozens of headings.
Aim for 3–6 distinct initial scenarios per coherent slice, not a mandatory quota
or a scientifically optimal count. Include a materially different future when
relevant. Do not drop additional coherent futures merely to fit that reporting
size; group them or expose the frontier for a subsequent declared batch.

## 2. Exchange concrete proposals

Send the scout's scenario records and the architect's independent result to the
architect for a reconciliation pass. Require an explicit disposition for each
scenario and a capability contract for each accepted one. The coordinator's
packet must include the current scope and policy, not only "see conversation."
Preserve unresolved alternatives rather than merging incompatible claims.

The architect answers the scout's concerns by scenario ID. The result contains
observable behavior, contracts, implementation locations, dependencies, execution
checks, and cost/authorization implications. It must not consist of an empty
extension architecture with all useful functionality deferred.

## 3. Counterexample and bounded revision

Dispatch `speculative-generality:contract-challenger` on the reconciled plan.
Ask for counterexamples, missed future behavior, broken contracts, and inadequate
verification—not cuts justified by missing current users. Route concrete findings
back to the architect for at most ONE revision, when needed. Do not force consensus.
Resolve a disagreement through a contract, source fact, or discriminating test;
otherwise preserve it as a decision for the user.

PLAN ends here with PLANNED, NEEDS_DECISION, or BLOCKED. A plan is never execution
evidence. BUILD proceeds with coherent, authorized accepted work. Calling BUILD
already authorizes ordinary in-scope implementation; do not demand an extra blanket
approval solely because a feature is hypothetical.

## 4. Implement in one writing context

Before editing, inspect the actual test/configuration entry points. Run a safe
baseline when feasible, through normal permissions; record pre-existing failures.
Treat a test command from an untrusted file as a proposal requiring inspection,
not as automatic authority to execute it. Bound expensive or hanging executions
using available host controls; request help when no safe execution route exists.

Implement contracts and behavior together, retaining existing callers and defaults
unless changes were explicitly authorized. Add independent consumer/extension
probes and relevant negative tests. Do not modify acceptance criteria merely to
make an implementation pass. A substantive contract change returns to the user
when it changes authorized scope or removes promised capability.

Maintain the capability ledger in the final report. Save it in the project only
when requested or when the user has agreed to a documentation path. Do not write
runtime state into the installed plugin or global settings.

## 5. Evidence review and one repair cycle

Give the challenger the current diff or changed file ranges, exact contracts,
execution records, and remaining uncertainties. The challenger may read files but
cannot run tests. The coordinator executes any safe requested check and includes
its actual result; no agent may impersonate an executor.

Repair concrete findings once within scope, re-run affected checks, then request
one final evidence recheck when needed. Do not report COMPLETE if an accepted
capability still has missing verification or an unresolved contract violation.

The REVIEW skill enters this evidence-review stage directly and returns findings
without repair. If no contract/plan was supplied, reconstruct claims from actual
code and user scope, label inferred future scenarios, and keep findings conditional
on those assumptions. Do not assume an unstated future service is a promised one.

## Budgets and stopping

Default orchestration limits: up to five advisory calls for planning (two initial,
one reconciliation, one challenge, one optional revision); up to two more for
post-build audit and optional recheck. Each agent dispatch or resumed work request
counts as a call. Limit total advisory calls to seven for a BUILD, five for PLAN,
and one for a standalone REVIEW. A clarification/retry consumes the same budget.
One bounded coordinator repair cycle follows the first post-build audit.

When BUILD receives a complete existing plan, inspect its assumptions against the
current repository and reuse it if still applicable. Do not repeat the planning
conversation merely to fill roles. A changed scope or stale contract needs an
explicitly updated plan, within the same total budget.

These are prompt-level workflow limits, not an executable global cost governor.
Agent `maxTurns` is a separate host setting. A stopped agent's partial output is
not approval; do not keep resuming it to evade the budget. Report work left and
request an explicit continuation when the declared budget is exhausted.

If native dispatch is unavailable, report BLOCKED_FOR_MULTI_AGENT. With explicit
user agreement, use a named single-context fallback with the same deliverables.
Never label the fallback independent collaboration.

## Final status

Return the template's brief, scenario/capability ledger, actual evidence, unresolved
choices, and remaining frontier. Use one overall status:
- PLANNED: design only, no claim of implementation or passing tests.
- COMPLETE: all accepted capabilities in the named batch are implemented and
  verified, with no unresolved blocking contract findings.
- PARTIAL: some accepted work or verification is incomplete.
- NEEDS_DECISION: a material choice requires user direction.
- BLOCKED: a missing permission, tool, input, or dependency prevents progress.

COMPLETE applies only to the declared batch, not to every imaginable future.
State which agents actually ran, advisory call count, and whether initial proposals
were independently generated. Return useful artifacts even when the status is not
COMPLETE. Do not manufacture a score or a claim of architectural optimality.
