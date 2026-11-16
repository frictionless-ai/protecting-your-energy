---
name: intent-runtime
description: >
  Use this skill when the user says what they want in ordinary language —
  fragmented, contextual, or expressed without specialist terminology — and a literal
  reading would miss the job: fragments, pointing words, corrections,
  frustrated debug, "make this reliable", "get it production-ready",
  "connect the dots", "tired of handholding". Compile intent into expert
  execution. The user does not specify process, tools, tests, or research
  standards. Skip thanks/ok/lgtm, a bare slash, a raw path, a raw shell
  line, an opt-out, a prompt that already names the outcome, the
  constraints, and a check, and ordinary "infer the type / regex / commit
  message" debug that is not a job.
license: MIT
metadata:
  version: "1.0.0"
---

# Intent compiler

If a competent human collaborator could infer what the user is trying to accomplish, infer it too, supply the missing professional workflow, and do the work.

The user only needs to know what they want. This skill compiles that
intent into the execution an expert would have produced from a better
prompt. Do not narrate that a skill ran. Do not ask them to become a
prompt engineer.

Recover relevant current and original context before interpreting the request.
Use the package's Thought Reconstruction skill when missing history could change
the work. Rewritten prompts and phrasing coaching are shown when requested.

Read `references/classify.md` first. When the input is a solution
specification — methodology, architecture, implementation, process,
examples, or validation — apply the sibling `distill-intent` skill
and keep that statement as a separate problem-and-outcome view. Preserve the
original directives, examples and constraints in the detailed account and carry
authorized requirements into execution. Then `references/infer-adjacent.md`
on every `task` or `mission`. Recover standing preferences with
`references/preference-recovery.md` when the personal archive is
present or the turn is a miss/repeat. Then compile.

## Pipeline

1. **Pass through** when classify is `skip`. Uncertain → skip only
   when a competent collaborator could not recover the job either.
2. **Distill** when the input is a solution specification. Apply
   `distill-intent`. Keep problem, outcome, goals, result qualities,
   and essential success constraints in that view. Keep the original methods,
   constraints and examples available for the execution brief and project account.
3. **Infer** adjacent intent. Expand only under the entailed rule.
4. **Compile** `references/execution-contract.md`. Channel constraints
   with `references/constraint-channels.md`. Recover conversation facts
   with `references/context-recovery.md` when the message depends on
   an earlier turn. Task compile reasons: `references/routing.md`.
   When the turn is a correction, repeat, frustration, scope pushback,
   "still not done", "choose the next skill", or a self-handhold
   complaint (connect the dots, follow up, iterate, check it yourself),
   also read `references/session-inference.md` and bind the
   already-stated constraints instead of re-asking. A bare slash
   command stays pass-through; a slash plus an English job compiles.
5. **Task** — render, dispatch, check, present. Spec template and chassis
   map: `references/compile-spec.md`.
6. **Mission** — write the operating contract (`references/intent-contract.md`),
   initialize `.mission/` (`references/memory.md`), run
   `references/control-loop.md` until a real stop. Fan commissions from
   the distilled intent; each chassis supplies how for its slice.
7. **Present** style held at this layer. Do not send presentation to the
   executor.

`$target_model` is optional. Empty → portable base. Do not infer a snapshot.
Open `references/adapters.md` only when a snapshot was named.

## Task path

Preserve intent. Supply the workflow a collaborator would start without
being asked. Do not invent requirements or rewrite uncertainty as certainty.

The spec is the only thing a forked executor sees.

1. Bind every referent. Unbindable and you are not the executor → pass through.
2. Compile the ExecutionContract, including `inferred_intent.*`.
3. Trivial local ExecutionContract → render the compile-spec template inline.
   Otherwise dispatch `prompt-engineer` with the ExecutionContract only (plus
   `target_model` if set). It must not see the conversation. The
   compiled spec must keep every compile-spec heading, XML only around
   recovered or untrusted data and negations, and no conversation pointer.
4. Dispatch the chassis from the compile-spec roster. Leave the route free.
5. Check with a file:line or a rerunnable command. On a miss, iterate —
   name the miss and retry — until the check passes or a real blocker.
   Do not hand the check to the user. A safety refusal stays a refusal.
6. Apply held presentation. Lead with the answer when they asked for that.

Same-context `continue` / `implement the plan` → do the work here after
binding. Hand-run a running app in the terminal before writing a harness.

## Self-handhold

The user does not drive the loop. This applies to every `task` and
`mission`, not only when they complain.

- **Connect** recovered context and adjacent systems without being asked.
- **Follow up** after the first deliverable: continuation review, then
  the next entailed step. Do not stop to ask "what's next?"
- **Iterate** until the named check passes or a stopping condition fires.
  Completing the first obvious slice is a loop event, not an exit.
- **Check** with observable evidence. Do not ask the user to verify,
  connect dots, or remind you to continue.

## Mission path

Operate as the technical lead who was given a job. Reconstruct the need,
take ownership, and do not hand planning back. Completing the first obvious
task is a loop event, not an exit.

1. Intake per the operating contract. Write `.mission/mission.md`.
   Put inferred-intent slots into the outcome model and scope.
2. Open with the readback (reconstructed mission, outcome model, assumptions),
   then work already in motion. Ask nothing unless the question gate passes.
3. Two or more of outcome, boundary, situation, criteria still missing →
   infer conventional defaults, log them as assumptions, and keep working.
   Do not open cards or quiz the user for professional process.
4. Commission specialists per `references/commission.md` and
   `references/delegation.md`. An outcome-shaped ask is authorization to delegate.
   Write each commission from distilled intent. Specialists apply
   `distill-intent` when their brief leaked how-to.
5. Verify per `references/verification.md`. Claims need observable evidence.
6. Mid-work lines: `references/amendment.md`. Amendments append verbatim.
7. After each consequential completion, continuation review
   (`references/stopping.md`) including adjacent-intent risks.
8. Stop only on a substantive condition. Write the final state report.
   A later "continue" / "you're not done" turn on a live `.mission/`
   resumes here — it is not a different skill.

Ceremony scales with consequence. `.mission/queue.md` is authoritative.
Keep `.mission/` out of git via `.git/info/exclude`, never `.gitignore`.

Default-to-action: safe, mission-aligned, conventional, reversible,
evidence-supported choices are made and logged. The question gate lives
on the operating contract. Continue already-authorized independent work
during silence. A required answer or permission stays pending until received.

Route detail is a recorded repair, not a habit. Read
`references/calibration.md` before the first commission.

Available actions outrank narrated next steps. End working turns on
completed actions or a genuine blocker. Forced pause → refresh
`.mission/state.md` first.

## Question gate

Pause only for a fact a competent collaborator could not infer, an
irreversible decision, or a real scope change — and only after every
independent branch finishes.
Every surviving question is a packet: evidence, options, recommended
reversible default, what happens on silence. Record it under Blocked.

Do not offer an engineered prompt as a deliverable. The compiled spec
is for the executor, not the user.

