# Optional Mission Runtime component

Keep changes inside the assigned component. Its workflows and skill variants
remain separate from neighboring components and root routes.

Current user instructions and host permissions govern execution. Resolve
component paths relative to this directory. Read README.md for bundled runtime
configuration and docs/prompt-style.md when editing prompt surfaces.

Telemetry is disabled by default. Preserve explicit opt-in, redaction and tool
capture choices. A disabled recorder never triggers substitute logging or an
automatic installer. Doctor probes require --probe and enabled recording.

Keep source archives, profiles, private event records, mission state, credentials
and historical evaluation cases outside this component.
