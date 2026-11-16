# Shared continuation and source-recovery adapters

These adapters carry the local continuation digest and archive-accounting guard into a portable checkout. Private source material, directive ledgers and guard state remain in the current user's configured locations.

## Entrypoints

| File | Input and output |
| --- | --- |
| `turn-digest.sh` | Reads hook JSON from stdin and prints continuation guidance plus the current workspace's open directive entries. `path [directory]` reports the ledger path and `add TEXT` appends a user directive for the current directory. |
| `turn-digest.sh json gemini` | Reads `cwd` and returns `hookSpecificOutput.additionalContext` for `BeforeAgent`. |
| `turn-digest.sh json cursor` | Reads `workspace_roots[0]` or `cwd` and returns `additional_context` for `sessionStart`. |
| `archive_guard.py --host claude` | Reads native `UserPromptSubmit`, `PreToolUse` and `Stop` payloads for Claude. |
| `archive_guard.py --host codex` | Uses the corresponding Codex payload fields. Confirm that the target client supports each configured event. |
| `opencode-turn-digest.js` | OpenCode v2 server plugin using `ctx.session.hook("context")` to append digest text before a model request. |
| `archive-reconstruction-rules.md` | Source acquisition, attribution, disposition, continuation and completion-accounting policy. |
| `recurrence-fix-class.md` | Recurring-correction and sibling-case follow-through guidance. |

Python 3 runs the guard. The shell digest requires a POSIX shell and standard Unix text tools. JSON output and JSON workspace extraction use `jq`. If `jq` is unavailable, JSON digest modes emit an empty object and the host proceeds. OpenCode uses Node's standard library and invokes the digest through `sh`.

## Host event wiring

The example JSON files are merge inputs. Preserve existing host hooks and register each behavior once. A plugin-managed registration and a direct user-config registration for the same entrypoint can duplicate every invocation.

- Claude can load the submit digest and guard for `UserPromptSubmit`, with the guard also receiving `PreToolUse` and `Stop`. The example uses the plugin-provided `CLAUDE_PLUGIN_ROOT`.
- Codex's example uses `PLUGIN_ROOT`. Hook availability and trust approval depend on the installed client. A configured file alone does not establish activation.
- Cursor's example supplies the digest through `sessionStart`. That event supplies startup context. Its `beforeSubmitPrompt` interface does not provide the same context-injection contract. A separate prompt-uplift hook requires its own integration.
- Gemini uses `BeforeAgent` and the Gemini JSON digest mode.
- OpenCode v2 loads `opencode-turn-digest.js` through its server plugin configuration. When installing the JavaScript away from this folder, set `PYE_TURN_DIGEST_SCRIPT` to the bundled digest's absolute path. Verify the target OpenCode API before enabling the adapter.

The guard currently accepts Claude and Codex host names. Cursor, Gemini and OpenCode use their digest adapters. Porting guard enforcement to another host requires a matching event adapter and actual host verification.

## Configuration and private state

| Variable | Meaning |
| --- | --- |
| `PYE_PLUGIN_ROOT` | Optional checkout root for skill paths emitted by the guard. It defaults to the checkout containing this file. |
| `PYE_ARCHIVE_ROOT` | Optional authorized local archive location named in recovery guidance. The task's explicitly supplied source roots can provide the location. |
| `ARCHIVE_RECONSTRUCTION_RULES` | Optional alternate rules document. The bundled rules are the default. |
| `ARCHIVE_GUARD_STATE_DIR` | Guard state directory. Existing local default is `~/.local/state/archive-reconstruction`. |
| `AGENT_LEDGER_ROOT` | Directive-ledger root. Existing local default is `~/.cache/agent-runs/ledger`. |
| `TURN_DIGEST_MAX_LINES` | Maximum open ledger lines included in a digest, default 40. |
| `PYE_TURN_DIGEST_SCRIPT` | Explicit digest script path for relocated wrappers and OpenCode integration. |

A workspace ledger can contain private directives. The adapter reads it locally and places the selected open entries into the active agent's context. Existing provider configuration and source access do not authorize a new external upload.

The guard routes source recovery and checks coverage receipts. Its lexical activation and shell-launch detection have limits. Accounting validation cannot establish semantic completeness, correct attribution or sustained user benefit. Comprehensive tasks retain explicit unresolved work and source-review obligations.

## Installation and verification

Use the host's existing plugin configuration or merge the relevant example after resolving its checkout variable. Preserve the old integration until the replacement has been observed in that host, then remove only the duplicate registration being replaced.

Verify that the correct event reaches the entrypoint, expected context appears once, routine requests remain routine, a scoped recovery retains its context, and a comprehensive task preserves incomplete coverage. Check current native client behavior before claiming cross-host parity. Installing these files does not start a background mission or scan an archive.

No local host configuration is changed by adding this directory.
