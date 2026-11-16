# Connect only when needed

Installing this skill supplies instructions. It does not register REA's MCP server, install Ghidra, or add tools to an agent that is already running.

If REA's tools are in your tool list, go straight to the target. Do not run `reentry doctor`, `rea doctor` or any setup before every investigation. Use the connected server's actual tool list and input schemas.

Run diagnostics only when something observable is wrong:

| Observed | Remedy |
|---|---|
| No `rea` tools in the list | `reentry doctor`. If REA is unregistered for this agent: `reentry setup --client <agent> --dry-run`, show the plan, then apply with approval. Restart the agent |
| Tools present, call blocked by the client | A client approval or policy setting, not a registration problem. Say so; do not re-run setup |
| REA reports a provider missing (Ghidra, Hopper, IDA) | `rea doctor --provider <name>`. Install nothing without approval. Continue with what is available and name the unavailable evidence |
| A bench tool missing (`afl-fuzz`, `re-agent`, `objdiff-cli`) | `reentry doctor` names the install hint. Lower the claim tier for the step that needed it; do not substitute an engine silently |
| Skill looks stale (references a tool the server does not advertise) | `reentry doctor --skill` compares installed copies against this repo |

Setup is additive and backed up. `--dry-run` writes nothing. Neither `reentry setup` nor `rea setup` installs Node, Java, Ghidra, IDA or any engine; they register and copy.

Shell `PATH`, client approval, registration and engine availability have different remedies. Do not repeat setup for all of them.
