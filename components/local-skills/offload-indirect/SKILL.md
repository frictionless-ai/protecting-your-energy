---
name: offload-indirect
description: >-
  Use on every session when information appears that would improve an existing
  user skill, plugin, or standing workflow — a better example, a reusable rule,
  a correction — even if the current task is unrelated. Also use when a skill
  is written to improve itself over time, or when chat history / side context
  would make a future session cheaper.
---

# Offload indirect

This skill will take work that is **not the current ask** and still worth
doing — skill improvements, capture-rule deltas, missing examples — and run
it in the background so the human does not have to remember.

The standing goal is brainlessness: infer intent, reduce back-and-forth, and
let future sessions inherit the better pattern.

## When a subagent will spawn

A background subagent will spawn when **all** of these hold:

1. **Reusable.** The fact would change a *future* session, not just this one.
2. **Named target.** One existing skill or plugin and an authorized private improvement log.
3. **Sharper than what is already written.** A new reject, a better example,
   a counted correction — not a restatement.
4. **Safe.** No secrets, tokens, other people's private messages, or
   dossier/psychoanalysis material.

If any gate fails, nothing will be spawned and nothing will be said.

## What the subagent will do

The parent will keep the user's task. The child will:

1. Read the named target and its existing improvement workflow.
2. Capture the supported delta in its authorized private log. Keep source attribution and omit private conversations.
3. Apply a shared skill change only when the current task authorizes that edit.

Use the host’s available background dispatch only when delegation is authorized. Otherwise retain the delta in the existing authorized task record while continuing the main work. One
target per spawn. Fresh context — no "as we discussed".

## What will not happen

| Excuse | Reality |
|---|---|
| "I'll mention it to the user" | That is the interaction this skill exists to remove |
| "I'll do it after I finish" | It will be forgotten. Spawn now or drop it |
| "I'll update every skill" | One target. The rest wait for their own gate |
| "This quote is colorful" | Color without a reusable rule will not be stored |
| "The current task is unrelated" | Unrelated is the point. That is why it is a child |

## Reuse and authorization

Living skills may invoke this gate when a better rule appears. The existing task and permitted files determine what can change. A historical suggestion or a loaded skill supplies no additional authorization. Preserve the user's current priorities and avoid creating a new question or approval step for routine authorized work.
