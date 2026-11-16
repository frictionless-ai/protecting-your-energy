# Compile spec

## Contents

- [Template](#template)
- [Dialect](#dialect)
- [Separation rubric](#separation-rubric)
- [Chassis map](#chassis-map)
- [Worked examples](#worked-examples)
- [Pre-dispatch check](#pre-dispatch-check)

The compiled spec is the only artifact that crosses the delegation
boundary. A forked or Task-spawned executor has no conversation
history. If a fact is not in this spec, the executor does not have it.

## Template

```
## Objective
<the real job in one or two sentences>

## Why
<only if it changes decisions; otherwise "n/a — does not change the work">

## Recovered context
- <fact> [stated|entailed|repo:path|default]
- <path> — read before acting

## Constraints
- <semantic constraint only>

## Scope
<what is in>

## Non-goals
<what a reasonable executor might add that this job does not want>

## Evidence
<observable check: command, file:line, or acceptance fact>

## Output
<executor report shape: findings with paths, or the change plus how to verify>

## Assumptions
- <assumption> [tag]

## Chassis
<roster name> — <one-line reason>
```

Identity is one sentence inside Objective or Why when tone matters to
the work (a security review vs a user-facing explanation). It is not a
persona stack. Task-spec failures dominate role-spec failures (MAST;
ratio version-dependent). Spend the budget on the objective, the
constraints, and the evidence line.

## Dialect

Markdown headers are the spec chassis. They are the hierarchy every
downstream model already knows.

XML wraps only recovered user data that must not bleed into
instructions: `<recovered>` facts, `<negation>` lines, pasted
artifacts. Do not XML-wrap the whole spec.

Pythonic shape is for branching routing only (`if the host is Fedora:
… elif Windows: …`). Use it when the job has mutually exclusive
paths. Do not turn a linear change into a class definition.

If the change is UI or audio: `if the surface is the studio: evidence
is a browser or replay check`. A narration of done is not that check
(same bar as a doc-review finding at confidence 75: a command or
file:line, not a claim).

## Separation rubric

Ask of each clause in the user's message and the recovered context:
*if this were removed, would the work or the correct answer change?*

| Survives into Constraints / Scope | Held as response style |
|---|---|
| Time range, quantity, environment, OS, toolchain | Tone, register, "plain English" |
| Source requirements, "only this repo" | Length, "less writing", "no intro" |
| "Exactly three alternatives" | "Show them as a table" |
| "Need code evidence / snippets as proof" | "Give me the answer first" |
| "Do not change tests" | "Don't sound like AI", second person |

"Need code snippets" is semantic when it is an evidence requirement
(the investigation is incomplete without them) and presentational when
it is only how the user wants the final message laid out. When both
readings fit, put an evidence requirement in the spec ("cite file:line
and quote the relevant lines") and keep "less writing" as style.

## Chassis map

Reuse the plugin roster. Do not invent a new agent.

| Job | Chassis |
|---|---|
| Map this repo / "what's in here" | repo-cartographer |
| External docs, providers, "look this up", "find something better" | research-analyst |
| Read-only role that no row fits | commissioned-analyst |
| Bounded implementation from a decided approach | implementation-engineer |
| Tests, coverage, flakes | test-engineer |
| Security defects, secrets, injection | security-reviewer |
| Correctness / maintainability review | code-quality-reviewer |
| "Why is this broken", repro, bisect | regression-investigator |
| Docs drift, README, changelog | docs-writer |
| Independent audit of a completion claim | adversarial-critic |

Default to one worker. Two to four only for a bounded comparison.
`adversarial-critic` is reserved for consequential completion claims —
a dispatch decision, not a standing extra hop.

## Worked examples

Examples are sanitized composites of real corpus families. They show
the split, not a required wording.

### Fragment + environment

Prior: "I only use Fedora KDE."
User: "what's the closest thing to winmerge?"

- Objective: recommend a two-way visual diff tool that is the closest
  practical equivalent to WinMerge for a Fedora KDE user.
- Constraints: Fedora; KDE-native or KDE-friendly packaging; visual
  two-way file/dir diff.
- Chassis: research-analyst.
- Style: none stated.

### Style mixed into the job

User: "look into this repo thoroughly. less writing more actual code snippets"

- Objective: survey the repository and report how it is put together.
- Evidence: quoted code with file:line — snippets are proof, not
  decoration.
- Chassis: repo-cartographer.
- Style (held): terse; lead with structure; no long preamble.

### Continuation

Prior: "find a visual diff tool closest to winmerge that runs on linux"
User: "yeah do that but only fedora"

- Objective: the prior recommendation task, now restricted to Fedora.
- Constraints: Fedora is hard, not a preference.
- Do not re-ask what "that" was.

### Frustrated debug

Prior: playlist view, bitrate column on, "low bitrate first" checked.
User: "why tf is it sorting it like this i have low bitrate first enabled"

- Objective: explain the actual sort and why it disagrees with the
  user's setting; fix if the setting is being ignored.
- Recovered context: the named setting and the UI surface.
- Chassis: regression-investigator.
- Style: match the user's register; do not moralize about profanity.

### Deixis

Prior discussion of meld vs kdiff3 vs kompare.
User: "what's this mean"

- Objective: explain the comparison just discussed (or the immediately
  preceding output if that is the referent).
- Recovered context: the three tools and the criterion they were
  scored on.
- If the referent is genuinely unrecoverable, one question packet, not
  a guess presented as fact.

## Pre-dispatch check

Before sending the Task:

- Every template heading is present and non-empty.
- No presentation clause is in Constraints.
- Recovered context is selected, not a transcript dump.
- Assumptions are tagged.
- Chassis is a real roster name.
- The spec does not point at "the conversation above."
