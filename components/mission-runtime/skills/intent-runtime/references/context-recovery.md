# Context recovery

A follow-up fragment is a complete task once earlier turns are folded
in. The current message is a delta, not the whole request.

## What to recover

Select facts that would change the work if omitted:

- Referents of `this`, `that`, `it`, `the thing`, `the same`, `do that`
- Environment and toolchain the user has already stated (OS, desktop,
  language, repo, host)
- Settings, error text, and file paths named earlier
- Corrections (`no, wait`, `i meant`, `only X`) — the amendment wins
- Quantities and time ranges that later turns narrow (`just july`)
- Dissatisfaction reasons that become recommendation criteria
- Session-pattern signals (frustration, repeat-ask, scope pushback,
  do-it-already). These mean a prior constraint was dropped, not that
  the user is starting a new job.

Do not recover:

- Greetings, thanks, and other closers
- The assistant's prior chain of tool calls
- Whole sibling reports (digest + path instead)
- Presentation preferences already held at the parent
- Facts that do not affect this job

## How far to look

Start with the immediately preceding user turn and the last assistant
result the user is reacting to. Walk backward only while new
load-bearing facts appear. Stop at a topic change or a completed
unrelated task.

A durable repo fact (`AGENTS.md`, `CLAUDE.md`, a file the user named)
is recovered by path: "read before acting." Do not paste it.

Resolve any authorized conversation archive from the current task or private
configuration. Search a relevant bounded slice for previously stated constraints
and unfinished work. Preserve exact source references and keep unrelated private
material outside the task. See `preference-recovery.md`.

A fact the user stated about themselves ("I only use Fedora KDE")
stays in Recovered context as `[stated]` until they amend it.

## Unrecoverable referents

If `this` / `that` has no recoverable antecedent in the conversation,
the open files, or a just-pasted artifact, do not invent one. Ship a
question packet: two or three concrete candidates, a recommended
default if one is likely, and the silence behavior. Work that does not
depend on the missing referent starts in the same turn.

## Corrections

A later turn that contradicts an earlier one is not ambiguity — it is
an amendment. Compile from the latest constraint set. Record the
superseded reading under Assumptions as `[stated, superseded]` so the
executor does not revive it.

## Size

Recovered context that exceeds a short bullet list is too much. Cut
anything that fails "would the work change without this?" Paths and
one-line facts beat paragraphs.
