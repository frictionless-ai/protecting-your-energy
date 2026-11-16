# intent-runtime

If a competent human collaborator could infer what the user is trying to accomplish, infer it too, supply the missing professional workflow, and do the work.

Follow `skills/intent-runtime/SKILL.md`. This plugin is an intent
compiler: natural language in, expert execution out. Adjacent intent
lives in `skills/intent-runtime/references/infer-adjacent.md` on every
task and mission. Preference and last-mile friction from the personal
archive: `skills/intent-runtime/references/preference-recovery.md`.
Skills follow https://agentskills.io/specification.

Classify → distill-if-needed → infer-adjacent → compile → fan-out.
A separate problem-and-outcome view may be distilled with `distill-intent`.
Preserve active directives, constraints, methods, and the detailed source account for execution.
Expand authorized scope only when tagged `[entailed]`. Do not write
ExecutionContracts to disk or telemetry.

`docs/solutions/` — documented solutions to past problems (bugs, best
practices, workflow patterns), organized by category with YAML
frontmatter (`module`, `tags`, `problem_type`). Relevant when
implementing or debugging in documented areas.

`CONCEPTS.md` — shared domain vocabulary (entities, named processes,
status concepts). Relevant when orienting to the codebase or discussing
domain concepts.
