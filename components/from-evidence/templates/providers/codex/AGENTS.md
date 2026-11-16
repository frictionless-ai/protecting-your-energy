<!--
Codex wrapper for the canonical skill.
Install: copy this whole directory to ~/.codex/skills/{{skill_name}}/ (personal)
or .codex/skills/{{skill_name}}/ (repo). Codex reads the same SKILL.md format.
Then merge the section below into the nearest AGENTS.md so Codex knows when
to load it. Invoke with `$` followed by the skill name.
-->

## {{skill_name}}

{{one_line}}

Load the `{{skill_name}}` skill when the user says any of the trigger phrases
in its description. Built from dataset `{{dataset_name}}` v{{dataset_version}}.
Quote its phrase bank as written. Its anti-patterns are hard rules.
