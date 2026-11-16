---
name: contextual-reply
description: Write the relevant next message in an ongoing conversation using earlier reasoning only where it answers the current move. Use for replies, follow-ups or bringing history into a present decision.
---

# Answer the present move

Resolve `PYE_PLUGIN_ROOT` to the installed Protect Your Energy package root before
using the commands below. Follow the skill symlink to its canonical component
location to find that root.

Bind the recipient, output author, latest actual message, unanswered question
and desired conversational move. Use current instructions and corrections.
Do not restart a background explanation that the recipient already understands.

When the reply continues saved work, capture current context with
`python3 $PYE_PLUGIN_ROOT/scripts/submission_context.py --harness codex`.
Use `--harness claude` when the calling client is Claude.
Supply the present request and corrections through its existing RAM-only stdin
submission; see [submission context](../../../../references/submission-context.md).
Resolve provisional task candidates from the live conversation and select a
relevant existing record internally with `--task-id` when needed. Keep the latest actual
message and audience authoritative over saved drafts. A self-contained reply
needs no saved-task capture.

Search relevant earlier episodes when they can change the reply. A supplied
excerpt is a cue, not a substitute for the archive. Use `reclaim` or the available
archive investigator for fragmented context. Verify author, source, chronology,
reply target and whether the owner adopted a prior suggestion. Read the episode
through its corrections and outcome; a shared topic alone does not establish
relevance. Broaden complementary sources if a narrow search misses the point.

Use the shared dense route at
`$PYE_PLUGIN_ROOT/scripts/archive_access.py query --query FACET`
or the default `reclaim` packet for semantic discovery. Follow original parent
locators and dated replies through fresh hydration pinned to the query's
generation. Check helper status and reported published scope; relevant sources
outside that scope require separate original investigation. Keep exact
lexical/path lookup explicit and repair runtime or locator failures.

Retain the smallest concrete episode and consequence that explain the current
ask. Keep motives and stakes when necessary to understand the reasoning; do not
attribute hidden motives to peers or reproduce irrelevant private material.
Preserve supported disagreement. A socially clear draft need not concede a
claim the owner rejects.

Distinguish whether context is useful from whether this is its moment. An
explicit current question or decision can make it useful now. Otherwise retain
it for a natural transition or requested briefing. Silence and a window switch
are not proof of availability. No unsolicited history dump or repeated alert.

Use `make-coherent` for meaning-preserving expression in the current register.
A short answer can preserve a named event, an important condition and a real
question. Do not reduce it to generic politeness or turn it into a report about
the reply.

For a DM/reply/follow-up, return only the paste-ready next message. A requested
brief or evidence report gets that artifact instead. Keep evidence privately.
Sending is separate from drafting and requires explicit authority. Do not expose
prompt architecture, diagnostic labels or raw archive details to the recipient.
