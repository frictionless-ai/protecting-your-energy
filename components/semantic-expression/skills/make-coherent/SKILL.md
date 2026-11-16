---
name: make-coherent
description: Turn rough, repetitive or associative explanations into coherent prose with precise concepts and the right detail for the audience, preserving meaning, creativity, disagreement and uncertainty.
---

# Express the thought clearly

Resolve `PYE_PLUGIN_ROOT` to the installed Protect Your Energy package root before
using the commands below. Follow the skill symlink to its canonical component
location to find that root.

Recover the intended outcome, audience and substantive meaning before editing.
Use the supplied text plus relevant context and latest corrections. Retrieve
the underlying original episodes first when the wording points to prior
thinking. Treat an incomplete description as a cue, not a literal specification
or a fixed example to repeat in later work. Retrieve
owner-authored examples suited to this setting when personal voice matters;
one mood or a technical register is not a universal personality. Use `reclaim`
when the meaning depends on fragments in earlier sources.

For a rewrite that continues saved work, first capture current context with
`python3 $PYE_PLUGIN_ROOT/scripts/submission_context.py --harness codex`.
Use `--harness claude` when the calling client is Claude.
Supply the current request and corrections through its existing RAM-only stdin
submission; see [submission context](../../../../references/submission-context.md).
Resolve provisional task candidates from the live conversation and select a
relevant existing record internally with `--task-id` when needed. Keep current input,
saved drafts and historical evidence distinct. A self-contained edit needs no
saved-task capture.

Use the shared local dense route at
`$PYE_PLUGIN_ROOT/scripts/archive_access.py query --query FACET`
for free-form semantic retrieval. `reclaim` now uses that same route by default
and carries original hydration into its private packet. Check helper status and
the query's published generation scope, then freshly hydrate relevant original
parents using the returned generation before rewriting. Exact lexical/path
lookup is a labelled supplement; a retrieval failure calls for repair. Inspect
relevant source families and dates outside the reported scope separately.

Preserve actors, causal links, conditions, negation, scope, time, necessary
versus sufficient claims, degree of certainty and attribution. Remove repeated
wording, not distinct reasoning. Separate a demonstrated result from a plan,
intuition, hypothesis or proposed mechanism. A more polished phrase must not
strengthen the evidence or erase legitimate disagreement.

Identify the described mechanism before choosing technical terminology.
Retrieve examples and the intended distinction from the owner's relevant archive context; verify uncertain or niche terms with primary/academic sources. Different processes can sound similar in rough language. Prefer plain
words when a familiar label would constrain a new idea or imply more than the
owner meant. Do not manufacture laws, diagnoses or scholarly corroboration.

Recover unstated connecting steps from the relevant wider context, including
subject/pronoun corrections and assumptions the owner later makes explicit.
Distinguish a necessary premise from optional background. Fill missing
connections when supported by the task and context. Keep new
mechanisms or consequential assumptions in a private interpretation ledger.
In the draft, distinguish a materially new commitment naturally when needed;
do not litter ordinary connective prose with processing disclosures.

Organize the piece around its useful claim, reason, mechanism and action, in
whatever form suits its audience. A reply, creative pitch and technical brief
can use different registers. Keep a good metaphor or expressive detail when it
carries meaning. Concision is not a uniform sentence-length or jargon rule.

Compare the completed draft with the original material for additions and lost
meaning. A factual statement can be true yet unfaithful to this request. Revise
for a concrete discrepancy, not because another model sounds more certain.
Check that a material recovered reason is actually expressed in the delivered
draft. Keeping it only in a source companion does not repair the reader's
missing connection. Retain only the depth this audience and moment need.
Read [methods](../../references/methods.md) when checking a difficult concept.

Deliver the rewritten artifact. For requested evaluation, provide the private
meaning map and actual checks separately. Outward copy does not expose prompts,
archive records, personal labels or diagnostic mechanics. Do not claim AI prose
was unaided human writing or remove audit evidence. Send/publish only with
explicit authorization.
