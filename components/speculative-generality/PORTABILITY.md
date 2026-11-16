# Compatibility and optional project integration

## Native target

This package is authored for **Claude Code**, based on the official plugin, skill
and subagent documentation inspected on 2026-09-22. This is a packaging decision,
not a claim that the historical experiments used Claude Code. The plugin has not
been loaded in a real Claude Code session in the build environment; native loading
and behavioral smoke tests remain to be performed. See VALIDATION.md.

Default directory discovery is used: `.claude-plugin/plugin.json`, root `skills/`,
and root `agents/`. No imaginary author/repository/marketplace URL is declared.
The policy is explicitly read by skills/agents; putting a `CLAUDE.md` at a plugin
root would not automatically load it as project instructions. [H1]

Current docs support `${CLAUDE_PLUGIN_ROOT}` in skill/agent content. Each skill
names its dependencies with that path, and each role reads its own policy. If
substitution or file access fails, the coordinator may supply exact policy text;
it must not silently work without the policy. [H1]

Agents use `name`, `description`, `tools`, `model`, and `maxTurns`. They deliberately
avoid plugin-agent `permissionMode`, `hooks` and `mcpServers`, which the inspected
host docs say are ignored for plugin subagents. The listed tools exclude shell,
editing, and delegation. Do not infer that every host version supports the same
fields; run the native validator and smoke test. [H2]

PLAN/REVIEW use the documented skill `disallowed-tools` field to remove common
write/execution tools on the invoking turn. This is additional hardening, not a
complete sandbox. Skills do not use `allowed-tools` to grant broad permissions.
Those are different settings: an allow list there is not a tool restriction. [H3]

No claim of compatibility with Codex, Cursor, Copilot, Gemini CLI, or another plugin
format is made. No cross-provider model routing or multi-machine service is shipped.

## Portable core, not an already-built adapter

The Markdown policy, protocol, role bodies, handoff and verification rules are
original, host-independent text. To port them, the host must provide separate agent
contexts, actual dispatch/results, read-only advisor permissions, source access,
and a permission-controlled editor/executor. Explicitly map those capabilities;
remove or replace host-specific frontmatter and path placeholders.

Use a single coordinator to relay structured messages. Supply scope and policy to
each role; do not assume the parent context is inherited. Preserve independent
initial inputs and disclose where the host cannot isolate them. Carry source/test
artifacts across phases rather than full chats. Porting this design is a task, not
a configuration option that already exists in this package.

For an environment with no subagents, the same prompts can be used sequentially in
one context only after user agreement. Label that mode as single-context and do not
report independent-agent benefits. The matched single-agent baseline in evals is
useful for testing whether native delegation is worth retaining.

## Optional project rule fragment

The following is original copy-ready text. Add it yourself only to a project's
actual instruction file after resolving any existing policy conflict. It does not
install or invoke the manual skills, and it should not be appended blindly:

> For explicitly selected speculative-generality tasks, implement hypothetical
> future capabilities proactively. Missing current users, a second implementation,
> or confirmed demand are not sufficient reasons to omit support. Require real,
> reachable behavior, explicit contracts and honest verification rather than empty
> abstractions or TODOs. Preserve stated compatibility, scope and safety constraints.
> Use the manually invoked speculative-generality workflow for role collaboration;
> do not claim the plugin ran merely because this preference is present.

## References

[H1] https://code.claude.com/docs/en/plugins-reference

[H2] https://code.claude.com/docs/en/sub-agents

[H3] https://code.claude.com/docs/en/skills
