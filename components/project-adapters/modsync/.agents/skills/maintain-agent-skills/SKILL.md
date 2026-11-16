---
name: maintain-agent-skills
description: >
  Use this skill when creating, rewriting, validating, or evaluating ModSync
  Agent Skills (SKILL.md, scripts/, references/, evals/). Use when the user
  mentions agentskills.io, skill frontmatter, progressive disclosure, trigger
  descriptions, or skill evals — even if they do not say "skill." Do not use
  for product install/diff work; those have their own skills.
license: BSL-1.1
compatibility: Requires Python 3. Requires skills-ref if you want official CLI validation.
metadata:
  author: ModSync
  version: "1.0"
  spec: https://agentskills.io/specification
---

This optional adapter uses the external checkout selected by `PYE_MODSYNC_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Maintain Agent Skills

Canonical skills live in `.agents/skills/<name>/SKILL.md`. Cursor and Claude
directories are discovery aliases. Do not invent a second copy of the body.

Read [the specification](https://agentskills.io/specification) and this repo's
[references/spec-checklist.md](references/spec-checklist.md) before editing.

## Checklist

- [ ] Directory name is `a-z0-9` + hyphens; no leading/trailing/consecutive `-`
- [ ] YAML `name` matches the directory (max 64)
- [ ] `description` is 1–1024 chars, imperative ("Use this skill when…"), user intent + when-not
- [ ] `SKILL.md` body stays under 500 lines / ~5000 tokens
- [ ] Extra detail goes in `references/` with a **when-to-load** sentence
- [ ] File links from `SKILL.md` are one level deep
- [ ] Scripts take flags/env/stdin only; `--help`; structured stdout; no TTY prompts
- [ ] `evals/evals.json` has 2–3 cases; `evals/trigger-queries.json` has ~20 labeled queries

## Workflow

1. Ground the skill in this repo (runbooks, failed installs, AGENTS.md). Do not generate a generic tutorial.
2. Write or edit `SKILL.md` (gotchas + default procedure; omit what the model already knows).
3. Validate:

```bash
python3 scripts/validate-skills.py
```

If `skills-ref` is installed: `skills-ref validate .agents/skills/<name>`.

4. If the description may misfire, load [references/trigger-evals.md](references/trigger-evals.md).
5. If output quality is in doubt, load [references/output-evals.md](references/output-evals.md).
6. If adding a script, load [references/scripts.md](references/scripts.md).

## Gotchas

- Discovery path `.agents/skills/` is the cross-client default (VS Code / Copilot). `.cursor/skills/` and `.claude/skills/` must resolve to the same folders.
- `name: pdf--processing` and `cloud_agent_starter` are invalid. Underscores are not allowed.
- A description that only says "helps with installs" will not trigger. Name the user intent (resume a fail-closed run, diff vs the manual tree).
- Do not pack two units of work into one skill (install + download + GUI). Compose skills instead.
- Do not put published mod titles in skill examples. See `anonymous-mod-fixtures`.

## Defaults, not menus

Edit the canonical file under `.agents/skills/`. Symlink aliases; do not fork bodies per client.
