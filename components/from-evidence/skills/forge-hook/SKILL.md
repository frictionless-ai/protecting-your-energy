---
name: forge-hook
description: >-
  Writes a hooks.json entry and, when needed, its script from a from-evidence
  dataset of things that went wrong or rules that were enforced by hand. Use
  when the user says "forge a hook", "turn these mistakes into a hook", "make
  a hook from the corrections", "automate the check I keep doing", or wants a
  PreToolUse, PostToolUse, Stop or SessionStart hook justified by real events
  rather than guessed.
---

# Forge hook

A hook automates a check the evidence shows a person did by hand, or a
failure the evidence shows happened. Without that evidence there is nothing
to automate.

## Evidence it consumes

A dataset whose records are incidents or manual checks: `topic` names the
event, `moves[]` includes the check (`verify_before_commit`,
`block_secret_write`, `load_context_on_start`), `outcome` shows what
happened when the check ran or was skipped, and `why_it_worked_or_failed`
states the rule.

Each hook needs at least two records showing the same check, or one record
with a costly `escalated` outcome.

## Steps

1. Read the records. Group by check. For each group write one line: event,
   condition, action, cost when skipped, with record ids.
2. Pick the narrowest event: `PreToolUse` to block or rewrite,
   `PostToolUse` to add context after, `Stop` to gate completion,
   `SessionStart` to load context, `UserPromptSubmit` to screen prompts.
3. Choose the type. Deterministic check and a script can express it:
   `command`. Judgement call: `prompt`.
4. Fill `${CLAUDE_PLUGIN_ROOT}/templates/hooks.json`. Placeholders:
   `event`, `matcher`, `hook_type`, `hook_key` (`command` or `prompt`),
   `hook_value`, `timeout`. Script paths use `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>`.
   Merge into an existing `hooks/hooks.json` without disturbing other
   entries.
5. For command hooks write the script, add a shebang, `chmod +x`, and
   check every binary it calls with `command -v`. The script reads JSON on
   stdin and prints `{"decision": "approve"|"block", "reason": "…"}`.
6. Cite. Put a `_evidence` comment next to the entry in the README or the
   script header: dataset, version, record ids, the rule sentence.
7. Test by triggering the event once. Record the observed output in the
   report.
8. Run `/evaluate-fidelity` in hook mode: cited ids exist, the rule
   sentence matches a record's `why_it_worked_or_failed`.

## Anti-patterns from evidence

Do not add a hook for a failure that happened once and cost nothing. Do
not widen a matcher beyond what the records show. If the records show the
check was skipped on purpose sometimes, the hook returns `ask_user`, not
`block`.

## Evolution hook

New incidents go into the dataset via `/evolve`. Rebuild the hook from the
updated records rather than editing the matcher by hand. Note the dataset
version in the script header so the next reader knows what it was built
from.

## Done when

- Event, matcher, type and script are justified by cited records.
- The hook fired once in a test and the output is in the report.
- The fidelity scorecard passes.
