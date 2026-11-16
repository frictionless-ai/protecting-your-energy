---
name: durable-codegen-capture
description: >-
  By default after code-generation work, capture a reusable high-quality task
  ledger entry (goal, constraints, durable artifacts, verified outcomes) and
  refine this skill’s quality gates when sharper focusable signal appears.
  Use for implement/fix/refactor/deploy/codegen sessions; skip chatty or
  low-signal turns. Prefer project ai-conversations/tasks/ when present.
---

# Durable codegen capture

Default behavior for **code generation** work: leave a reusable task record
others (and future you) can continue from — not a transcript dump.

## When to apply

Apply automatically when the user asks to implement, fix, refactor, deploy,
generate, wire, migrate, or otherwise **produce/change code or configs**.

Skip when the turn is only Q&A, status chatter, “briefly inform…”, forge/session
complete notices, or exploration with no durable code change.

## Quality gate (hard)

Capture **only** if **all** of these hold:

1. **Clear goal** — one operator intent in a sentence (not a chat log).
2. **Durable artifacts** — concrete paths, commands, URLs, schema names, or PR
   refs that still matter tomorrow.
3. **Verified outcome** — something actually landed, failed with a root cause,
   or is in-progress with a measurable status (counts, tests, health checks).
4. **Reuse value** — a future agent could resume without re-reading the whole
   transcript.

**Do not capture / do not append:**

- System notification text, skill dumps, tool-trace noise
- Speculative brainstorms with no decision or artifact
- Secrets, tokens, full env files, or private message bodies
- Near-duplicate updates that add no new focusable fact
- Raw conversation dumps “for completeness”

When the gate fails: do the code work, say nothing about a ledger write (or one
line: “skipped capture — low signal”).

## Where to write

Pick the first that exists / fits:

1. `<project>/ai-conversations/tasks/` if that tree exists  
2. Else `<project>/.cursor/task-ledger/tasks/` (create if needed)  
3. Else ask once where the project keeps task notes; do not invent a third
   parallel “current” ledger

Also keep/update an index if present (`ai-conversations/INDEX.md` or
`.cursor/task-ledger/INDEX.md`). Prefer running the project consolidator when
available:

```bash
python3 ai-conversations/consolidate.py
```

…then **edit** the matching task file so outcomes are accurate (consolidator
snippets can be stale or off-topic).

## Task file shape

Filename: `YYYY-MM-DD-<slug>.md` (UTC or local date of the goal).

```markdown
# Task: <one-line goal>

- status: planned | in_progress | blocked | done | cancelled
- session: `<id-if-known>`
- updated: <ISO-8601>
- quality: pass   # only write files that pass the gate

## Goal

<operator intent, cleaned>

## Constraints

- <only binding constraints>

## Durable artifacts

- `path/or/url` — why it matters

## Outcome

- Landed: …
- Partial / blocked: …
- Next: …

## Reuse notes

- <what a future agent must know; no narrative padding>
```

**Update in place** when the same goal gains focusable facts. Prefer editing the
existing task over creating a twin. New file only for a clearly separate goal.

## Reusable improvements

When a new capture rule is supported, record it only in an authorized private workflow log. Include the reason and a sanitized example. Apply shared skill edits only within current authorization. Preserve source history and avoid storing raw conversations.

## Completion

Finish the requested code work, evaluate the capture gate, and update the existing task record and index when it passes.
