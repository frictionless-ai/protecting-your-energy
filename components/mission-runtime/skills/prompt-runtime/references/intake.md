# Intake

Recover first. Ask second. Compile third. The current message is a
delta, not the whole request.

A lookup, a review, a debug, or a named one-line edit is not a
create. A prompt that already names the outcome, the constraints, and
a check skips intake and compiles.

## Contents

- [Recover first](#recover-first)
- [How far to look](#how-far-to-look)
- [Search order](#search-order)
- [Auto-answer](#auto-answer)
- [Creates](#creates)
- [Packets](#packets)
- [Corrections](#corrections)
- [Stop](#stop)

## Recover first

Select facts that would change the work if omitted. Reconstruct the
job at full fidelity from what is already available:

- This conversation, including `this` / `that` / `the thing` / `do that`
- Generalized pointers ("the previous task", "what we were doing",
  "the same as before") — expand to the full constraint set, not a
  one-line gloss
- `.mission/` when it exists
- `docs/` (plans, research, architecture) and project instruction files
- The repo
- Environment, toolchain, settings, error text, paths, quantities,
  and dissatisfaction reasons the user already stated

A generalized pointer is not unrecoverable until those sources have
been searched. Write every load-bearing fact into the spec — outcome,
constraints, decisions already made, rejected alternatives, evidence.
Omitting a known constraint because the user abbreviated is the
failure this step exists to prevent. If a question can be answered by
reading, read.

Do not recover greetings, the assistant's tool-call chain, whole
sibling reports (digest + path), presentation preferences, or facts
that do not affect this job.

Cut anything that fails "would the work change without this?" Do not
drop a load-bearing fact to keep the list short: a gloss that expands
to eight constraints keeps all eight. Paths and one-line facts beat
paragraphs. A durable repo fact travels as a path plus "read before
acting."

## How far to look

Start with the immediately preceding user turn and the last assistant
result the user is reacting to. Walk backward only while new
load-bearing facts appear. Stop at a topic change or a completed
unrelated task — except when the current message is a gloss of a
prior task: then walk back to that task and expand it.

A fact the user stated about themselves ("I only use Fedora KDE")
stays as `[stated]` until they amend it.

## Search order

Name the gap before searching (target, approach, scope, current
state), so the search has a stop.

1. Conversation — prior turns, open files, just-pasted artifacts.
2. Repo — failing tests, recent commits, named errors, the files a
   fragment could mean.
3. Local docs — README, `docs/`, project instruction files, `.mission/`
   when present, the path the user already named.
4. External — only when the job needs a current fact the repo cannot
   supply.

Stop the walk when new facts stop changing the work. A multi-file or
architecture question is a job for a read-only chassis
(`repo-cartographer`, `research-analyst`); the parent keeps the
digest. A single named path is a direct Read. Pass a forked worker
everything it cannot see: the fragment, the error string, the files
already ruled out.

Document findings as tagged facts (`[stated]`, `[repo:path]`,
`[entailed]`). Those become Recovered context or question options,
not a research essay.

## Auto-answer

When those sources settle a branch and the user has not redirected,
take that answer. Tag it. Do not ask them to restate it. A later
recommended choice stays consistent with the settled branches.

## Creates

When the job is a new artifact, feature, plan, design, surface, or
subsystem, this step runs before compile and before anyone builds
the thing.

A redirect ("scrap that, do Y instead") is an amendment: recover the
new direction. Do not revive the old one as if it were still in force.

Only remaining branches that still change what gets created:

1. Name the decision in one sentence.
2. Ask one question. Give the recommended answer and why.
3. Resolve it — their pick, or the recommendation on silence.
4. Recurse into the next dependent branch. Park independents.

Do not stack questions in one turn. A list of open branches is for
the runtime, not the user. Independent inspection runs during
recovery. Building the new artifact waits.

Bands are a starting set (no ablation in this repo). Count remaining
questions after recovery, not questions imagined before it. A larger
create earns a deeper tree, not more trivia.

| Size of the create | Remaining questions |
|---|---|
| Named micro (one file, already shaped) | 0 — compile |
| Bounded (one chassis, one surface) | At most one, the highest-leverage gap |
| Multi-surface or architectural | Dependent branches that change the build, one at a time |
| Mission-shaped | The four decision inputs; at most three remaining cards |

## Packets

A question packet that is not grounded in a finding is a quiz. Ask
only what search cannot decide. Every surviving question is one
decision. Options come from findings, not from base knowledge:

- two to four concrete options, each a thing that exists (a file, a
  pattern, a trade-off the repo already took)
- A one-line stake for each option so the pick is informed
- A recommended default when one option is the conventional or
  reversible choice
- What happens on silence (the default fires)
- Work that does not depend on the answer starts in the same turn
  — except the new artifact of a create, which waits

"Other approach" is not an option. If the finding set is empty, the
gap is unrecoverable — say so, and still start the independent work.

| Open decisions after search | Packets |
|---|---|
| One missing referent or fork | 1–2 |
| Scope and approach both open | 3–4 |
| A major feature with several real forks | at most 6 |

More than six means infer conventional defaults, log them, and keep
moving. A questions-only turn is last resort: the missing fact would
make the answer wrong or unsafe.

## Corrections

A later turn that contradicts an earlier one is not ambiguity — it is
an amendment. Compile from the latest constraint set. Record the
superseded reading under Assumptions as `[stated, superseded]` so the
executor does not revive it.

## Stop

Intake ends when remaining branches are defaultable, the user
selected hands-off, or the job is already specified. Then compile.
Do not start a new artifact while a load-bearing branch is still
open and not defaultable.
