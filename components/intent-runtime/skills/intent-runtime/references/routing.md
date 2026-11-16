# Routing

This table is the `task` compile router after classify.

Test: can this executor act correctly on the context it will receive?
Uncertain → `complete` (pass through). Casual register is never a reason.

| Reason | Do |
|---|---|
| `complete` | Pass through |
| `protected` | Pass through |
| `needs-context-expansion` | Bind G1/G6 into `relevant_context` |
| `correction` | G2 first; keep negations |
| `needs-artifact-framing` | G3: fill `artifacts` + objective |
| `needs-task-clarification` | G4: synthesize `success_conditions` as assumptions |
| `needs-scope-normalization` | G7: stage success; do not shrink scope |

## Gaps

- **G1** — `continue`, `continue <workflow>`, `implement the plan`, `any remaining work`, `try again`, unbound `it`/`that`. Long `continue` that states a new task is not G1.
- **G2** — `no kill it`, `i meant X not Y`. Priority. Not a new task.
- **G3** — dump + `please fix` / `how to fix?`
- **G4** — `make it better`, `tidy this` with no done-condition
- **G5** — prior failures the executor cannot see → `previous_failures`
- **G6** — env facts in session, not in the message
- **G7** — one-liner for a long project. Pause only for destructive work, scope change, or user-only input.
- **G8** — `be concise`, `json only`. Not a gap. Route the channel.

## Never compile

- `/command`
- raw shell or path
- `stop rewriting my prompts` (session opt-out)
- autonomy-grant-only
- same-agent `continue` when you will execute here
