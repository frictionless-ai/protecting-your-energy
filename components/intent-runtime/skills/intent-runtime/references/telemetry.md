# Optional local telemetry

Telemetry supports inspection of elapsed time, tool counts, delegation, and outcomes. These measurements require interpretation of the actual result before judging usefulness.

Recording defaults off. The parent plugin does not activate these component templates. When a host adapter is deliberately configured, `scripts/mr_record.py` still requires an explicit telemetry opt-in. An absence of records may mean disabled or unavailable recording.

## Configuration

The store defaults to `${XDG_STATE_HOME:-~/.local/state}/protecting-your-energy/intent-runtime/telemetry`. A store-local `config.json` may configure `enabled`, `redact_text`, `capture_tool_io`, and size limits. Environment controls take precedence.

| Control | Effect |
|---|---|
| `MISSIONRUNTIME_TELEMETRY=on` | Enable local recording |
| `MISSIONRUNTIME_TELEMETRY=off` | Disable all recording |
| `MISSIONRUNTIME_REDACT=1` | Replace text with length and digest |
| `MISSIONRUNTIME_HOME=<path>` | Override the private store |

Defaults are `enabled=false`, `redact_text=true`, and `capture_tool_io=false`. Raw payloads are omitted when either redaction is enabled or tool I/O is disabled. Existing explicit private configuration can override defaults.

Enabling unredacted text or tool payload capture requires the user's authorization for that capture. Preserve ExecutionContracts outside telemetry. Keep transcripts, paths, and peer information in the authorized private data boundary.

## Host setup and interpretation

`scripts/mr_install_hooks.py --host <host>` previews a project-scoped merge. `--apply` writes it with a backup. User-wide setup requires `--scope user`. Host trust and event support determine whether hooks run.

Use `scripts/mr_report.py --help` to inspect report options. The recorder uses local files and makes no network calls. Its failure-open behavior allows the host turn to proceed if recording fails. Record processing failures and missing observations when interpreting results.

Do not bypass disabled recording by hand-writing fallback logs. A separate agent-written outcome note needs its own user-authorized storage scope. Cost counts alone cannot establish successful execution or improved engagement.
