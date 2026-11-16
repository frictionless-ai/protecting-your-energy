# prompt-uplift

[![CI](https://github.com/bodencrouch/prompt-uplift/actions/workflows/ci.yml/badge.svg)](https://github.com/bodencrouch/prompt-uplift/actions/workflows/ci.yml)

prompt-uplift compiles a short or underspecified user message into an
explicit prompt (an ExecutionContract) for the model that will do the work,
then checks the result against that contract. You can keep saying things
like "continue" or "fix this"; the skill binds referents and constraints
before the executor runs. It does not change intent, authority, or scope.
Casual tone by itself is not a reason to rewrite.

## Install

**1. The skill.** Copy the directory into a Claude Code skills location:

```bash
# this project only
cp -r skills/prompt-uplift .claude/skills/prompt-uplift
# all projects
cp -r skills/prompt-uplift ~/.claude/skills/prompt-uplift
```

Optional: install the renderer subagent for larger contracts.

```bash
cp skills/prompt-uplift/agents/prompt-engineer.md ~/.claude/agents/
```

Without that file, the skill still renders with its built-in portable
template. The subagent only isolates rendering for bigger jobs.

**2. The hook (optional).** The skill description is how Claude Code finds
uplift. The hook marks a turn so the skill is considered on that turn.
Merge the `hooks` block from `hooks/settings.example.json` into
`.claude/settings.json` or `~/.claude/settings.json`, and set the absolute
path to `hooks/prompt_uplift_hook.py`.

The hook only injects a fixed `PROMPT_UPLIFT_CANDIDATE` marker through
`additionalContext`. It does not rewrite the prompt, spawn agents, or write
prompt text to disk. If the hook errors, the turn continues unmarked.

Smoke-test:

```bash
echo '{"session_id":"s1","hook_event_name":"UserPromptSubmit","prompt":"continue"}' \
  | python3 hooks/prompt_uplift_hook.py
# prints hook JSON with the marker

echo '{"session_id":"s1","prompt":"/help"}' | python3 hooks/prompt_uplift_hook.py
# no output (protected class)
```

To opt out for a session, say something like "stop rewriting my prompts".
The hook writes an empty flag file under `$XDG_RUNTIME_DIR/prompt-uplift/`
(or `/tmp/prompt-uplift/`; override with `PROMPT_UPLIFT_STATE_DIR`) and
stays silent for that session.

You can also invoke the skill by hand. `target_model` is optional. If you
omit it, the skill does not infer a model and does not load adapter notes.

```
/prompt-uplift
/prompt-uplift target_model=gpt-5.6-sol
```

## How to test

From the repo root. These scripts use the Python stdlib and do not call a
model:

```bash
python3 -m unittest evals.test_subagent_dispatch -v
python3 evals/run_trace.py reddit-tiktok-ideas
python3 evals/run_trace.py --all
```

`run_trace.py` also accepts a raw message:

```bash
python3 evals/run_trace.py --message 'continue' --context 'finish the tests' --executor fork
```

Trigger-calibration and invariant grading need a live agent session. Those
steps are in [the upstream evaluation guide](https://github.com/bodencrouch/prompt-uplift/blob/main/evals/README.md). This repo does not ship
API clients or a live A/B runner.

## Layout

```
skills/prompt-uplift/          the Agent Skill (install this)
  SKILL.md                     trigger description + compilation pipeline
  references/                  loaded on demand by the skill
    routing.md                 routing reasons, gaps G1-G8, pass-through classes
    execution-contract.md      the IR schema + invariants I1-I5
    constraint-channels.md     constraint classification and channel owners
    adapters.md                snapshot-keyed adapter registry + execution hints
  agents/prompt-engineer.md    optional forked-context renderer subagent
hooks/
  prompt_uplift_hook.py        UserPromptSubmit interceptor (mark, don't rewrite)
  settings.example.json        hook registration snippet
evals/                         trigger corpus, invariant cases, A/B methodology
  harness/                     CI-runnable dispatch tracer (no model calls)
  reddit-pairs/                OP-lazy → rewrite-intersection gold pairs
  test_subagent_dispatch.py    hook / isolation / gold-pair tests
  run_trace.py                 print one case's subagent payloads
```

## Privacy

prompt-uplift does not log raw prompts. The hook marker has no user
content. The ExecutionContract stays in conversation state and is not
written to disk. Eval cases are paraphrased message shapes, not verbatim
posts or dataset rows.

Provider retention still applies to whatever the executor receives. See
[SKILLS.md](SKILLS.md) §9.

## Design docs

- [SKILLS.md](SKILLS.md) — design rationale (Rev. 2). Not loaded at runtime.
- [IMPLEMENTATION-NOTES.md](IMPLEMENTATION-NOTES.md) — where the shipped
  code differs from that design.
- [Upstream evaluation guide](https://github.com/bodencrouch/prompt-uplift/blob/main/evals/README.md) — evaluation sources maintained with the original component.
- [CONTRIBUTING.md](CONTRIBUTING.md) — tests and how to add a gold pair.

## Optional live evaluation source

The [live-eval procedure](skills/live-eval/SKILL.md), scorecard, recorder and
component-local runner/grader prompts are bundled for explicitly requested live
evaluations. Cases, datasets and model execution remain external. The recorder
validates by default and writes only with `--write`, using private XDG state or
an explicitly configured destination. Text retention requires `--include-text`.
These optional files add no root routes, host agents or hooks automatically.

MIT. See [LICENSE](LICENSE).
