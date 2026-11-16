---
name: mission-telemetry
description: >
  This skill should be used when the user asks about mission-runtime telemetry,
  benchmarking, or measurement — phrases like "is mission-runtime worth it",
  "how much did that mission cost", "benchmark the runtime", "show mission
  stats", "what did the agents do", "turn telemetry off", "stop recording my
  prompts", "where is the telemetry stored", or "/mission-telemetry". It reports
  recorded run data, checks that recording is actually working, and changes the
  telemetry configuration.
metadata:
  version: "0.6.0"
---

# Mission telemetry

Report effective recording settings and existing cost records from the configured
local store. Resolve scripts relative to this optional component directory.

Use `python3 scripts/mr_doctor.py` for read-only inspection. A disabled recorder
is an intentional state. Keep it disabled unless the user requests recording.
The `--probe` option writes only when recording is already enabled.

Use `python3 scripts/mr_report.py`, with `--sessions` or `--json` when needed,
to inspect existing records. Describe missing coverage explicitly. Cost counts
alone do not establish quality or benefit.

## Capture choices

`MISSIONRUNTIME_TELEMETRY=on` opts in to recording and `off` disables it.
`MISSIONRUNTIME_REDACT=1` retains text lengths and hashes. Raw prompt storage
requires explicit `MISSIONRUNTIME_REDACT=off` or `redact_text: false` in the
private config. `capture_tool_io` defaults to false and requires a separate
explicit choice. `MISSIONRUNTIME_HOME` configures the private store.

The optional installer defaults to project scope and dry-run output. Use
`--apply` only with authorization to configure that host, and preserve existing
hooks. All records remain local. Source transcripts are separate from telemetry.

Read [telemetry](../mission/references/telemetry.md) for configuration and the
shared capture boundary. Historical records and exact prompt text remain private.
