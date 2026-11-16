# Optional local telemetry

Telemetry is disabled by default. Its purpose is to measure elapsed time,
tool calls and delegated work. Counts alone do not establish whether the
result helped the user.

## Enable only when requested

Keep disabled telemetry disabled across hooks, direct recorder calls and
fallback paths. A missing or empty store is expected while recording is off.
Never create substitute records to bypass the user's choice.

`MISSIONRUNTIME_TELEMETRY=on` enables recording. Text remains redacted by
default and tool input/output capture remains off. Explicit
`MISSIONRUNTIME_REDACT=off` permits prompt text retention. Enable
`capture_tool_io` separately in the private config only when requested.
Raw payload storage requires both unredacted text and tool I/O capture.

Private configuration is `~/.missionruntime/config.json`, or `config.json`
under `MISSIONRUNTIME_HOME` when configured. Supported keys are `enabled`,
`redact_text`, `capture_tool_io`, `max_text_chars` and `max_payload_bytes`.
Environment switches take precedence. Invalid boolean values retain defaults.
Records stay local under the configured store. Source archives and transcripts
are separate inputs and never become telemetry sources implicitly.

## Host setup

This optional component is bundled as source. Registering its telemetry hooks
requires a separate explicit host setup. Its Claude hook template expects the
component directory as `CLAUDE_PLUGIN_ROOT`. Other host templates can be merged
with `scripts/mr_install_hooks.py --host <host> --scope project`. The installer
prints a plan by default. `--apply` writes a merged file and backs up existing
configuration. Preserve other hooks and disabled-hook settings.

## Inspect recording

`python3 scripts/mr_doctor.py` reports effective configuration and available
records. It does not activate recording or write a probe by default.
`--probe` requests a recorder probe only when recording is already enabled.
`python3 scripts/mr_report.py` summarizes existing records. Use `--sessions`
for per-session output or `--json` for structured output.

Invoke these scripts relative to this component directory, even when the
umbrella plugin provides a different `CLAUDE_PLUGIN_ROOT`.

## Boundaries

The recorder always exits zero so telemetry failures cannot block the host.
Use the recorder for explicitly requested events. Manual records require the
same explicit opt-in and redaction choices, and must not duplicate hook events.
Keep private prompt text and event records out of published artifacts. Any
claim of workflow improvement needs observed outcomes alongside cost data.
