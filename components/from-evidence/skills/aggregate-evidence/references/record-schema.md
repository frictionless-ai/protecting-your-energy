# Record schema

One JSON object per line in `records.jsonl`. Exact field names. No extra
fields; `scripts/validate.py` rejects them.

```json
{
  "id": "r-001",
  "source": "chat-export",
  "medium": "chat",
  "partner": "collaborator-a",
  "ts": "2026-01-10T09:00:00Z",
  "topic": "whether to switch the test runner",
  "turns": [
    {"ts": "2026-01-10T09:00:00Z", "author": "collaborator-a", "text": "..."},
    {"ts": "2026-01-10T09:01:00Z", "author": "self", "text": "..."}
  ],
  "moves": ["ask_for_the_run", "name_the_threshold"],
  "outcome": "conceded",
  "why_it_worked_or_failed": "One or two sentences.",
  "quality": 5
}
```

| Field | Type | Rule |
|---|---|---|
| `id` | string | Unique in the dataset. `r-NNN` is the convention. Never reuse an id after deleting a record. |
| `source` | string | Must match a `kind` in `dataset.json` `sources[]`: `discord`, `chat-export`, `notes`, `email`, `forum`, `synthetic`. |
| `medium` | string | `chat`, `dm`, `thread`, `email`, `call-notes`, `issue`. |
| `partner` | string | Role label. Never a real name or handle. |
| `ts` | string | ISO-8601 of the first turn. |
| `topic` | string | One line, lowercase, no trailing period. |
| `turns[]` | object | `{ts, author, text}` in order. `author` is `self` for the subject, otherwise the partner label. At least one `self` turn. |
| `moves[]` | string | Non-empty. snake_case. In the order they happen. |
| `outcome` | string | `conceded`, `convinced`, `redirected`, `stalled`, `escalated`, `dropped`. |
| `why_it_worked_or_failed` | string | One or two sentences naming the deciding move. |
| `quality` | int | 1 to 5. See `quality-bar.md`. |

## dataset.json

```json
{
  "name": "<directory name>",
  "version": "0.1.0",
  "pattern": "<one sentence>",
  "sources": [{"kind": "chat-export", "path": "<where it came from>", "note": "<what was scanned>"}],
  "record_count": 3,
  "held_out_ids": ["r-003"]
}
```

`record_count` must equal the number of lines in `records.jsonl`. Every
held-out id must exist. At least one record must not be held out.

## Text rules

- Keep the subject's text verbatim, including typos and lowercase. The
  phrase bank is quoted from it.
- Partner text may be trimmed to the part the subject responded to. Mark
  trims with `[…]`.
- Replace names, handles, product names and links with role labels or
  `[link]`. Do not paraphrase around them.
