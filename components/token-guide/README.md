# Token Guide

Quiet, optional suggestions when an agent session repeats an expensive workflow pattern. The hook returns brief context for the agent. It never returns a tool denial or changes permissions, and errors exit without blocking the session.

The component contains the advisory hook, the reusable workflow skill and a local audit command. The parent plugin owns host-hook wiring. Installing these files alone does not establish that a host has loaded the hook.

## Use the guidance

The skill covers independent-call batching, proportional context loading, reuse of prior investigation, useful work during waits, compact worker packets and verification matched to the task.

Hints are conditional suggestions. Preserve the requested scope, necessary source reading, existing ownership and actual verification requirements. A pattern match can be wrong about dependencies or why a call was necessary.

[Token Guide skill](skills/token-guide/SKILL.md) · [Hook configuration](hooks/hooks.json)

## Audit a selected session

```sh
python3 tools/audit.py /path/to/a/selected-session.jsonl
```

The command reads the supplied transcript and any adjacent subagent transcripts. It reports observed usage, timing and estimated workflow costs to stdout. Keep the input and output in private configured locations. No transcripts, audit results or private historical session accounting are packaged here.

Input-equivalent-token calculations use configurable coefficients. The historical defaults are `TG_READ=0.1`, `TG_WRITE_1H=2.0`, `TG_WRITE_5M=1.25` and `TG_OUT=5.0`. Set them for the accounting scenario you intend to inspect. They do not establish current provider prices. Estimated opportunities can overlap, and timing attribution is heuristic.

[Measurement guidance](docs/measurement.md)

## Hook behavior and configuration

The hook supports `UserPromptSubmit`, `PostToolUse`, `PostToolUseFailure` and `PermissionDenied` payloads. It reads a bounded transcript tail for relevant hints. A permission-denied event can record a hint for a later tool result and never retries or authorizes the denied action.

Each hint has a per-session cooldown. State is private runtime data under `$XDG_STATE_HOME/protecting-your-energy/token-guide`, using `~/.local/state` when XDG_STATE_HOME is absent. `TOKEN_GUIDE_STATE_DIR` selects another private state directory. Writes use private temporary files and atomic replacement. Concurrent events can still race on advisory counters.

- `TOKEN_GUIDE_OFF=1` returns immediately without guidance or state access.
- `TOKEN_GUIDE_BIG_CONTEXT` configures the batching threshold, default 200000.
- `TOKEN_GUIDE_HUGE_CONTEXT` configures the compaction threshold, default 600000.
- `TOKEN_GUIDE_BIG_OUTPUT` configures the large-result threshold, default 25000 characters.
- Cooldown values and other heuristic limits are declared in `hooks/guide.py`.

Malformed or nonpositive threshold settings fall back to their defaults so a configuration typo remains advisory.

Python's standard library is the runtime dependency. No model calls, network service or provider credentials are used by this component.
