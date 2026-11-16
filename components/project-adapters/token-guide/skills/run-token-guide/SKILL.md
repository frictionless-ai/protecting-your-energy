---
name: run-token-guide
description: Run, test, smoke-test, replay or debug the token-guide hook plugin. Use to check which hint fires for a payload, replay a real session transcript, tune thresholds, or reinstall the plugin.
---

This optional adapter uses the external checkout selected by `PYE_TOKEN_GUIDE_ROOT`. Read the [bundle index](../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# run-token-guide

token-guide is a Claude Code hook (`hooks/guide.py`). It reads a hook payload on stdin and prints either nothing or one `additionalContext` hint. You drive it by piping JSON into it. Paths below are relative to the repo root.

## Prerequisites

`python3` (standard library only) and the `claude` CLI for install.

## Run (agent path)

Replay the fixture payloads, plus a real transcript to see what a live session would get:

```bash
.claude/skills/run-token-guide/smoke.sh ~/.claude/projects/<project>/<session>.jsonl
```

It prints `ok`/`FAIL` for 68 cases and exits non-zero on any failure. Cooldown state goes to a throwaway `TMPDIR`, so every run starts fresh.

One payload by hand:

```bash
echo '{"hook_event_name":"PostToolUse","session_id":"x","tool_name":"Bash","tool_input":{"command":"until curl -s localhost:8080/x; do sleep 5; done"}}' | python3 hooks/guide.py
```

## Audit a session

```bash
python3 tools/audit.py ~/.claude/projects/<project>/<session>.jsonl
```

It prints wall-clock (active, away, model, tools, and time parked on each background job) and, per pattern, what was wasted, the measured cost in input-equivalent tokens, the cheaper path and the fix. "Independent calls" is an upper bound: a call can depend on a decision the previous result informed. Gaps over 30 minutes count as the user being away.

## Install

```bash
claude plugin validate .
claude plugin marketplace add "$PWD"
claude plugin install token-guide@token-guide
```

Hooks load at session start, so a running session keeps its old hook set.

## Tuning

- `TOKEN_GUIDE_BIG_CONTEXT` (default 200000) is the context size at which the batching hint can fire.
- `TOKEN_GUIDE_HUGE_CONTEXT` (default 600000) is the size for the compact hint.
- `TOKEN_GUIDE_BIG_OUTPUT` (default 25000 chars) is the tool-result size for the `bigout` hint.
- `TOKEN_GUIDE_OFF=1` silences all hints.
- Cooldowns per hint are in `COOLDOWN` in `hooks/guide.py`.

## Gotchas

- The transcript splits one assistant response across several JSONL lines that share one `usage`. Count turns by `message.id`, or streaks and costs come out doubled.
- A streak rule of "all N turns single-call" never fired on real sessions, because an occasional 2-call turn breaks it. The rule is 6 of the last 8.
- Cooldown state is per `session_id` under `$TMPDIR/token-guide/`. Replaying the same payload twice in one state dir is silent the second time. That is by design, not a bug.
- `run_in_background` Bash calls are never flagged as polling, because they are the recommended fix.
- The plugin ships the `token-guide` skill too, so `token-guide` is listed in `~/.agents/.claude-sync-ignore`. That keeps Claude from loading a second copy through the `~/.agents` sync.
- `notify` counts `Agent`/`Task` calls that are not explicitly `run_in_background: false` (background is the default), 3 within 20 minutes. Foreground parallel batches stay quiet.
- The matcher includes `Workflow` and `Skill` so `fanout` and `skillchain` can fire; reinstall or restart the session after changing `hooks.json`.
- `PermissionDenied` hooks cannot return `additionalContext` (their output only takes `retry`). The guide records the denial in session state and attaches the `compound` hint to the next tool result instead.
- `PostToolUseFailure` payloads carry `error`, not `tool_response`. Auto-mode rejections show there as "auto mode cannot determine the safety of …".
- A `Read` result nests the file text under `file.content`. Measuring the raw JSON made every read look like one huge line; `resp_text` unwraps it.
- Match `ugrep: error` only at the start of a line. Otherwise any output that quotes it, such as grepping this repo's smoke fixtures, triggers the hint.
- Agent prompts are classified on `task_text()`: a pasted debate block is stripped first. Before this, a protocol pasted at the top pushed the task past the first 600 characters and `packet`, `research` and `dualreview` never saw it.
- `dualreview` keys on the first commit hash in the task text. Later hashes are usually parents and caused false pairs.
- Bash checks run on `strip_heredocs()` output, so polling words or `pgrep -f` inside a heredoc (scripts, test data, hint strings) do not fire.
- `serial` and `rerun` read the wall clock; `TOKEN_GUIDE_NOW` overrides it so the smoke driver can replay time gaps.
