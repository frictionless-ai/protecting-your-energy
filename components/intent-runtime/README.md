# intent-runtime

This component helps an agent recover a user's intended outcome, organize the task, and execute authorized work. It includes the intent-runtime and distill-intent skills, specialist role prompts, a prompt marker, and reusable compilation and inspection helpers.

Recover current conversation context and relevant original evidence before filling gaps. Preserve explicit methods, constraints, examples, corrections, and deliverables. A distilled problem-and-outcome view is a separate reading aid alongside the detailed account.

## Bundled layout

- `skills/` contains the two skills and their reference procedures.
- `agents/` contains specialist prompts.
- `hooks/` contains optional host templates and the content-free context-recovery marker.
- `support/harness/` contains reusable compilation, inspection, routing, and evaluation-schema helpers relocated from the original harness.
- `scripts/` contains command-line adapters and optional telemetry tools.
- `integrations/` contains optional project-scoped Cursor adapters.

The parent plugin exposes the skills through root routes. Nested host adapters require deliberate configuration. Copying this component does not establish that every host has activated its hooks.

## Optional host integration

The Cursor project template needs `INTENT_RUNTIME_ROOT` set to this component's installed directory when copied outside this tree. Its wrapper delegates to the canonical marker hook.

`python3 scripts/mr_install_hooks.py --host cursor` previews a project-scoped telemetry hook merge. Add `--apply` to write the displayed target. Existing settings are merged, duplicate commands are avoided, and a backup is retained. `--scope user` selects user-wide configuration explicitly.

Telemetry defaults off. Explicitly enabling it retains redaction and disables tool-input/output capture. Its private store defaults to `${XDG_STATE_HOME:-~/.local/state}/protecting-your-energy/intent-runtime/telemetry`. `MISSIONRUNTIME_HOME` overrides that location. See the telemetry reference before enabling additional capture.

## External evaluation material

Private cases, transcripts, generated runs, model artifacts, mission state, and evaluation-only GitHub workflows are excluded from this component. Reusable schema and runner code is retained. Case and output roots are configurable with `INTENT_RUNTIME_EVAL_CASES`, `INTENT_RUNTIME_EVAL_DATA`, and `INTENT_RUNTIME_EVAL_WORKSPACE`. Runner help can be viewed without invoking a provider. Evaluation commands require separately supplied cases and any runner dependencies they name.

Archive-mining commands require an authorized archive root through their CLI option or `THOUGHT_RECONSTRUCTION_ARCHIVE` / `PYE_ARCHIVE_ROOT`. Personal names for derived-corpus redaction may be supplied as the JSON array `INTENT_RUNTIME_REDACT_NAMES`. Raw archives stay external.

## License

MIT. Original copyright and attribution are preserved in LICENSE. Integration changes preserve the original source checkout.
