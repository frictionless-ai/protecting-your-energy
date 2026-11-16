---
name: skill-library
description: Find and load on-demand skills and agents that are not preloaded (security, ECC, awesome-skills, cyber, UI, marketing, research, writing), plus role prompts for subagents (language, devops, QA, research and orchestration roles). Use when a task needs specialised know-how not covered by loaded skills, or before spawning a worker that needs a specialist role.
---

# Skill library

More skills live on disk in `~/.agents/skill-library/` than are loaded into the session. Codex and Claude Code do not scan that folder, so they cost no catalog space until you load one.

1. Search: `skill-lib search <words>`. Use two or three plain words, such as `skill-lib search react router` or `skill-lib search accessibility audit`. Use `skill-lib list [collection]` to browse.
2. Read: `skill-lib show <name>`. It prints the SKILL.md and the files bundled with it. Use `collection/name` if the name is ambiguous.
3. Follow that SKILL.md for the task. Resolve its relative paths (references/, scripts/) against `skill-lib path <name>`.
4. Make one always-on only when the user asks: `skill-lib enable <name>` (undo with `skill-lib disable <name>`).

When a loaded skill names another skill that is not loaded, look it up here. For example, `better-interface` routes to `better-accessibility`, `better-layout`, `better-writing`, `better-typography`, `better-colors` and `better-ui`; load each with `skill-lib show <name>`.

## Roles for subagents

Library agents are role prompts, not native subagent types. To give a worker a role, run `skill-lib show <agent>` and put the file body, after the frontmatter, at the top of the worker's task packet. Then spawn the tier that fits (`basic-worker`, `standard-worker`, `deep-worker` or `frontier-worker`). Browse roles with `skill-lib list voltagent` or `skill-lib search <role words>`. Many roles from the large skill collections (`rust-pro`, `reverse-engineer`, `c4-context`) are stored as skills, and they work the same way.

Many VoltAgent roles have a `## Communication Protocol` section with JSON requests to a `context-manager` agent. No such agent runs here. Cut only that section, up to the next `## ` heading, and drop any other line or JSON block addressed to `context-manager`. Keep the `## Development Workflow` section that follows it, because it holds the role's method.

If `skill-lib` is absent from PATH, run `python3 <skill-directory>/scripts/skill-lib`. Set `SKILL_LIBRARY` to an existing catalog root containing `INDEX.tsv`, `skills/` and `agents/`. Set `SKILL_CORE` to the host’s opt-in skill registration directory when enabling skills. The catalog and its third-party contents remain external.

Read each source and follow its applicable instructions. Catalog inclusion supplies discovery metadata. Inspect origin, license and current applicability before importing third-party content.
