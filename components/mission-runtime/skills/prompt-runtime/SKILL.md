---
name: prompt-runtime
description: >
  This skill should be used when the user's message is a real task that
  would execute poorly if taken literally — create or build asks
  ("build this", "create a", "add a feature", "grill me"), short
  follow-up fragments ("yeah do that", "just july", "only fedora"),
  deixis ("what's this mean", "the thing", "do the same for that one"),
  frustrated debugging ("bro why is this broken", "why tf is it
  sorting like this"), vague lookup or replacement ("look this up",
  "find me something better this thing sucks"), a correction after the
  original ask, or a mix of the job with how the answer should read
  ("less writing", "plain English", "give me the answer first"). It
  reconstructs a self-contained execution spec from the conversation,
  delegates the work, and applies presentation preferences only when
  answering the user. Do not use for thanks/ok/lgtm, talk about the
  assistant itself, a one-line typo fix that already names the file,
  or a prompt that already names the outcome, the constraints, and a
  check.
when_to_use: >
  Casual, lazy, slangy, typo-filled, or context-dependent task
  messages, including create/build asks that still need a recovered
  spec. Skip thanks/ok, questions about the assistant,
  already-specified coding tasks, and one-line named typo fixes.
metadata:
  version: "0.6.0"
---

# Prompt runtime

The user is allowed to write like a human. This skill does the prompt
engineering: recover the intended task from the conversation, compile a
self-contained execution spec, delegate the work, and render the result
in the user's preferred style. The user should not have to know this
happened.

Read `references/intake.md` before the first compile — always on a
create, a fragment, or a turn that would become a question. Read
`references/compile-spec.md` before the first compile. Read
`references/evidence-calibration.md` when the compile would name
files, APIs, or architecture.

## Intake

Recover first. Write the job at full fidelity, including what a gloss
was standing in for. Auto-answer settled branches unless the user
redirected. Interview only remaining branches that still change the
work, one at a time, each with a recommended answer. Thoroughness
follows the size of the job. A create that already names the outcome,
the constraints, and a check skips intake. Building a new artifact
waits on remaining load-bearing branches; other work does not.

## When not to engage

Skip this skill, and do not rewrite, when:

- The message is an acknowledgment or close (`thanks`, `ok`, `lgtm`).
- The user is talking about the assistant or about prompting, not
  asking for work.
- The prompt already names the outcome, the constraints, and a check —
  do the work; do not inflate it.
- The ask is a single named micro-edit (`fix the typo in README line 4`)
  with no missing context.

A skip is a decision, not a failure. Minimal intervention is the
default for an already-strong prompt.

## Compile

Preserve the user's actual intent. Add the minimum structure that makes
execution reliable. Do not invent requirements, silently broaden scope,
or rewrite uncertainty as certainty. When a missing detail can be
inferred from the conversation or the repo, infer it and tag it. When
several implementation choices are reasonable and the user does not
care, leave the choice to the executor.

The spec is the only thing the executor will see. It must stand alone.

Match the rewrite to the prompt. Already complete → minimal or no
rewrite. Clear but messy → tidy only. Vague but answerable → infer,
tag assumptions, keep moving. Blocked by a fact only the user has →
question packet, and still start the work that does not depend on it.

Slots (all present, all non-empty; see the reference for the template
and worked examples):

1. Objective — the real job, not the literal fragment.
2. Why — only when it changes decisions.
3. Recovered context — selected facts from earlier turns, the repo, and
   attachments. Paths, not pastes, when the content lives on disk.
4. Constraints — semantic only (see below).
5. Scope and non-goals.
6. Evidence — what would show the job is done.
7. Output — the executor's report shape, not the user's reading style.
8. Assumptions — each tagged `[stated]`, `[entailed]`, `[repo:]`, or
   `[default]`.
9. Chassis — which specialist from the plugin roster, and why.

## Task vs presentation

A constraint enters the spec if removing it could change *what work is
done or what answer is correct*. It stays at this layer, as response
style, if it only changes *how the finished result reads*.

Quantities, time ranges, environment, source requirements, and "exactly
N alternatives" are semantic. Tone, length, formatting, persona, "give
me the answer first", and "don't sound like AI" are presentation.
Ambiguous cases default to the spec.

Do not send the presentation block to the executor.

## Delegate

Treat the executor as a capable specialist. Send the spec; leave the
route free. Do not ask it to expose reasoning, and do not add ritual
scaffolding the executing model already knows.

Map the job to a chassis using the compile-spec roster. Score
complexity, urgency, locality, taste, and volume before picking a
shape. A probe is one cheap check that the mechanism fires; a ruler
is the evidence slot's full bar. The spec travels as the Task prompt.
After the report returns, spot-check file:line or a rerunnable command
before integrating.

An independent non-authoring check is a dispatch decision for
consequential changes, not a standing sentence in every spec.

### Hand-run before harnessing

When the job builds or changes an app, spend the first verification
round in the terminal against the running thing — invoke the binary,
call the endpoint, read the process table. Inline commands are
reactive: a wrong assumption surfaces in the next command, while a
harness written first encodes the assumption and then confirms it.

Write the script, fixture, or unit test after those invocations settle
the behavior, built from the commands that actually proved it — that is
when the reusable shape is known rather than guessed.

Boundary: `curl -s localhost:4173/api/health | grep webuiEnabled`
settles whether the daemon serves the UI. A fixture asserting
`webuiEnabled === false`, written first, settles only that the fixture
agrees with itself.

## Render

Apply the held presentation preferences to the finished answer. Lead
with the answer when the user asked for that. Keep the user's register
and language when they wrote in them (identifiers stay as-is). Do not
narrate that a skill ran unless they ask. Do not print the compiled
spec, XML scaffolding, or an internal checklist. The user sees the
work, not the rewrite.
