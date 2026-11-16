# Bundled scripts

Load this when adding or changing files under a skill `scripts/` directory.
Source: https://agentskills.io/skill-creation/using-scripts

## Rules

- No TTY prompts. Flags, env, or stdin only. Missing required flag → error + usage.
- `--help` documents flags, examples, and exit codes.
- Data on stdout (prefer JSON). Diagnostics on stderr.
- Distinct exit codes. Idempotent where agents may retry.
- Destructive work needs `--dry-run` and an explicit `--confirm` or `--force`.
- Default to a short summary if output can exceed ~10K characters; paginate with `--offset`.
- Paths in `SKILL.md` are relative to the skill root. Run scripts from there or pass `--root`.
- Pin versions for `npx`/`uvx` one-offs. Declare Python deps with PEP 723 if needed.

## This repo

Repo install helpers stay in `scripts/agents/`. Skill scripts are only for skill-local checks (frontmatter, one-writer, checkpoint restore flags).
