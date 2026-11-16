# Specification checklist

Load this when validating or authoring a skill. Source: https://agentskills.io/specification

## Directory

```
skill-name/
├── SKILL.md
├── scripts/      # optional
├── references/   # optional
├── assets/       # optional
└── evals/        # this repo: evals.json + trigger-queries.json
```

## Frontmatter

| Field | Required | Rules |
|---|---|---|
| name | yes | 1–64, `a-z0-9-`, no leading/trailing/consecutive `-`, equals folder |
| description | yes | 1–1024, what + when |
| license | no | short |
| compatibility | no | 1–500 if present |
| metadata | no | string keys and values |
| allowed-tools | no | space-separated, experimental |

## Progressive disclosure

1. Catalog: name + description only (~50–100 tokens)
2. Activation: full SKILL.md (<5000 tokens / <500 lines)
3. Resources: load when the body names them and says **when**

Relative paths are from the skill root. Do not chain references more than one hop.
