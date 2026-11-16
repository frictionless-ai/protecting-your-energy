# Mission Runtime

This optional source component retains Mission Runtime's nine skills, eleven
specialist agents, reference material and local telemetry tools. Its
`intent-runtime` and `distill-intent` skills are separate variants from those in
the neighboring Intent Runtime component.

Bundling these files leaves existing host activation choices intact. The
umbrella plugin does not route these skills or load these hooks automatically.
Use this component only when the active task selects its workflow. Resolve its
scripts and references relative to this directory.

## Included workflows

The skills cover intent compilation, intent distillation, prompt preparation,
long-running missions, elicitation, resumption, progress reporting and telemetry.
Read their `SKILL.md` files under `skills/` for the individual entry points.
Specialist roles remain under `agents/`. Current user instructions and host
permissions govern every workflow.

Python scripts use the standard library. Run `python3 scripts/mr_record.py --help`,
`python3 scripts/mr_report.py --help`, `python3 scripts/mr_doctor.py --help` or
`python3 scripts/mr_install_hooks.py --help` for command details. No model,
provider or archive processing runs when these modules are imported.

## Telemetry choices

Recording is disabled by default. `MISSIONRUNTIME_TELEMETRY=on` opts in.
Enabled recording redacts prompt text and omits tool inputs and results by
default. `MISSIONRUNTIME_REDACT=off` explicitly permits prompt text retention.
Tool capture needs `capture_tool_io: true` in the private configuration.
Raw payload storage requires both unredacted text and tool capture.

`MISSIONRUNTIME_HOME` selects the local store. Otherwise the store is
`~/.missionruntime/`. Configuration lives at `config.json` under that store.
An existing explicit configuration can enable capture. Environment switches
take precedence. Invalid configuration retains disabled, redacted defaults.

The doctor is read-only by default. Its `--probe` option requests a local
record only when recording is already enabled. A disabled store needs no repair.

## Optional hook setup

Hook templates remain under `hooks/`. The Claude template expects this
component directory as `CLAUDE_PLUGIN_ROOT`. Loading the umbrella plugin does
not register it.

The installer defaults to project scope and prints a proposed configuration.
Explicit `--apply` merges supported hook arrays, retains existing settings and
creates a backup. Explicit `--scope user` selects a host-wide target. Host
support and trust requirements need verification in the chosen client. No
installer was executed during bundling.

## Source and limitations

The source plugin is [Mission Runtime](https://github.com/bodencrouch/mission-runtime),
version 0.6.0. Its manifest declares MIT licensing and credits bodencrouch.
The [source license notice](LICENSE-NOTICE.md) preserves that declaration.

Private profiles, mission state, transcripts, existing host settings, evaluation
cases and runners, historical research reports and model data remain outside
this bundle. Context and preference recovery use task-selected or privately
configured source locations. The prompt workflows describe intended behavior.
Bundling and static verification do not establish live host behavior or a
measured improvement in task outcomes.

[Architecture](docs/architecture.md) and [prompt style](docs/prompt-style.md)
retain reusable source design and authoring guidance. Source-only verification
commands named in historical authoring guidance require their original tooling.
