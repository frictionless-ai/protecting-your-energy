# Task template

```markdown
# Task: <one-line goal>

- status: planned | in_progress | blocked | done | cancelled
- session: `<id-if-known>`
- updated: <ISO-8601>
- quality: pass

## Goal

<operator intent, cleaned>

## Constraints

- …

## Durable artifacts

- `path` — …

## Outcome

- Landed: …
- Partial / blocked: …
- Next: …

## Reuse notes

- …
```

# Reject checklist

Skip capture if any are true:

- [ ] No durable path/URL/command/test result
- [ ] Goal is only status/notification/harness text
- [ ] Content would need secrets to be useful
- [ ] Duplicate of an existing task with no new fact
- [ ] Would only restate the transcript
