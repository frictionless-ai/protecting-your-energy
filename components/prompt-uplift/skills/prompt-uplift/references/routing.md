# Routing reasons

Routing is categorical — the reason *is* the compilation plan. A message may
carry several reasons. When uncertain, route `complete` (pass through).

The criterion for every reason: **can the actual target executor act
correctly using the context it will receive?** The same message routes
differently depending on the delegation boundary — "continue" is `complete`
when the current agent executes, `needs-context-expansion` when a
fresh-context subagent will receive the task.

| Reason | Meaning | Contract consequence |
|---|---|---|
| `complete` | Executor can act correctly on the message as-is | Pass through |
| `protected` | Slash command, raw payload, opt-out, autonomy-grant-only | Pass through |
| `needs-context-expansion` | Referents or environment facts must be bound before delegation (G1/G6) | Bind antecedents into `relevant_context` |
| `correction` | Supersedes an in-flight instruction (G2) | Priority handling; `negations` + explicit supersession note |
| `needs-artifact-framing` | Artifact present, task statement missing (G3) | `artifacts` + synthesized `objective`/`deliverable` |
| `needs-task-clarification` | No success conditions recoverable (G4) | Synthesized `success_conditions`, marked as assumptions |
| `needs-scope-normalization` | One-liner hiding a long-horizon project (G7) | Staged contract + autonomy policy |

## Executor context gaps (what to look for)

- **G1 — unbound referents at the delegation boundary:** "continue",
  "try again", "both A and B please", "do the file dialog thing last",
  "ask that question again". Gap: the antecedent.
- **G2 — corrections to in-flight work:** "no kill it", "i meant the
  codebase, not the README", "not that version — the installed one".
  High severity if misread as a new task. Always carries priority.
- **G3 — artifact dumps without framing:** a large pasted log/code block or
  screenshot plus a tiny instruction ("please fix", "how to fix?"). Gap:
  what the artifact is, what "fixed" means, what deliverable is wanted.
- **G4 — goal without success conditions:** "improve the performance",
  "tidy the codebase". Gap: definition of done. Synthesize it, marked as
  an assumption — never as a user statement.
- **G5 — prior-failure context the executor can't see:** frustration or
  repetition ("I told you a million times…", "none of those respected the
  ignore file…"). Gap: which approaches already failed and why. Feed
  `previous_failures`, neutrally.
- **G6 — scattered or implicit environment facts:** OS, versions, paths
  present in the session but not in the message.
- **G7 — scope-explosion one-liners:** a multi-week project in one sentence
  ("fully reverse engineer X and rewrite it cross-platform"). Normalize
  scope without shrinking it; set autonomy policy (verify milestones
  internally, continue through reversible in-scope work, pause only for
  destructive/irreversible actions, real scope changes, or user-only input).
- **G8 — inline response-shape constraints:** "just the one-liner pls",
  "quickly and shortly", "do not summarize". Not a gap — a channel-routing
  job; see constraint-channels.md.

## Register note

Slang, profanity, lowercase, "pls", DM-style prose are **not deficiencies**
and never trigger uplift by themselves. "wtf is dockstarter? what does it do
that portainer wouldn't?" is a complete prompt. When a message is casual AND
has a real gap, compilation naturally normalizes register while preserving
technical content, negations, and emphasis ("that looks ugly af" → the
aesthetic judgment survives as a hard constraint; the register doesn't).

## Pass-through classes (never uplift)

- App-level commands: any `/command` — byte-for-byte pass-through.
- Short-but-fully-specified imperatives when the executor is the current
  agent: "zip the current directory", "write it in rust."
- Raw payloads: bare shell lines, bare paths.
- Explicit opt-out: "stop rewriting my prompts" (disables uplift for the
  session).
- Autonomy grants: "you have permission, hurry up and do it all" — this is
  authority policy that flows into the contract of whatever task it governs;
  it is never itself rewritten.
