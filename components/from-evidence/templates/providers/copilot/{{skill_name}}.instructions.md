---
applyTo: "**"
---

<!--
GitHub Copilot wrapper for the canonical skill.
Install: this file to .github/instructions/{{skill_name}}.instructions.md and
the sibling SKILL.md + reference.md + dataset/ to .github/skills/{{skill_name}}/.
-->

# {{skill_name}}

{{one_line}}

When the user says a trigger phrase from `.github/skills/{{skill_name}}/SKILL.md`,
follow that file. Built from dataset `{{dataset_name}}` v{{dataset_version}}.

## Phrase bank

{{phrase_bank}}

## Never

{{anti_patterns}}
