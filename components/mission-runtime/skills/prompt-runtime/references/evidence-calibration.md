# Evidence calibration

Prompt specificity must not exceed evidence specificity. A compiler
that has not inspected the project must not design the implementation.
The executor that *will* have the repo should be told what to inspect,
not handed invented names.

## Contents

- [Levels](#levels)
- [Ceiling](#ceiling)
- [Discovery targets, not facts](#discovery-targets-not-facts)
- [Self-check](#self-check)

## Levels

### C0 — request only

The compiler has the ask and nothing inspected: no repository, logs,
screenshots, or runtime.

Allowed: desired behavior, stated constraints, stated non-goals,
discovery instructions, verification outcomes, safety and scope.

Forbidden as facts: unsourced paths, symbols, frameworks, commands,
env vars, schemas, APIs, UI architecture, or step lists that assume
unknown structure.

Default: a lean discovery-first spec. The objective is the outcome.
Recovered context names what to read, not what the unread files
contain.

### C1 — partial evidence

The compiler has some exact user-supplied material (a snippet, error,
screenshot, file name, stack name, or log) but not the whole project.

Allowed: those exact facts, labeled hypotheses, instructions to verify
the clue against the repo.

Do not convert a likely location into a confirmed one, a sample name
into an existing symbol, an error into a proven root cause, or a
screenshot into a design system.

### C2 — verified evidence

The compiler inspected the relevant files, config, tests, docs, or
runtime, and that evidence is available now.

Allowed: observed paths, symbols, commands, versions, data flow, and
conventions; an implementation direction the evidence supports.

Still forbidden: filling remaining gaps with confident guesses.

## Ceiling

| Level | What the spec may state as fact |
|---|---|
| C0 | Outcome, supplied constraints, discovery path, done criteria |
| C1 | Exact supplied facts + labeled hypotheses + verification |
| C2 | Verified details with traceable evidence |

Missing information is not permission to invent. Mark unknowns. Point
at the inspection the executor can do.

## Discovery targets, not facts

At C0 or C1, the spec may list *questions the executor should answer
from the repo* — entrypoints, the existing test command, the nearest
pattern, callers of a named symbol the user supplied. Those are
search orders for terrain, not claims that the answers are already
known.

A desired UI outcome is not a palette, typeface, component library, or
layout system. Those enter the spec only from product requirements,
brand evidence, repo patterns, or a supplied visual reference.

## Self-check

Before a spec names a file, function, framework, package, command,
test, env var, route, or UI part: say which level applies and where
that name was observed. If it was not observed and the user did not
supply it, drop it or mark it `[default]` / a hypothesis.
