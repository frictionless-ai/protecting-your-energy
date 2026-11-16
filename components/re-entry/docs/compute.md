# Shared compute

Closed by default. The seam exists so two people can lend each other machines for a campaign without standing up anything they then have to maintain. Nothing in this file is implemented; the refusal path and the `Job`/`Receipt` schema are design targets, and [status.md](status.md) tracks when they land.

## Where it fits

Everything expensive in the loop is already a **job** with hashed inputs and a receipt as output: a compile-and-objdiff attempt, a BSim ingest, a fuzz campaign, a PANDA replay, a VeriBin run. Jobs are pure in the sense that matters: same inputs, same tool versions, same result. That is what makes them movable.

So shared compute is not a new layer. It is a second consumer of the job queue:

```
local agent ──proposes──▶ coordinator ──enqueues──▶ job queue
                                                      │
                               ┌──────────────────────┼──────────────────────┐
                               ▼                      ▼                      ▼
                        local worker          friend's worker          friend's worker
                        (same machine)        (over tailnet)           (over tailnet)
                               │                      │                      │
                               └──────── receipts ────┴──────────────────────┘
                                                      ▼
                                       coordinator verifies, arbiter commits
```

Workers never touch Ghidra, the identity store, or the exports. They take a job, fetch its inputs by hash, run the tool, and return a receipt plus artefacts by hash. The arbiter on the owner's machine stays the only writer. A remote worker that lies produces a receipt that fails re-verification; it cannot corrupt state.

## The three pieces, and what each already is

| Piece | What it is when the path opens | Why it is small |
|---|---|---|
| Network | A tailnet (Tailscale or Headscale). Workers are peers by hostname; no public ports, no TLS to manage | Identity and encryption come from the tailnet. The project adds none |
| Queue | Temporal task queues, one per tool class (`compile-objdiff`, `bsim`, `fuzz`, `replay`). A worker registers for the classes it can run | Temporal already does retry, heartbeat, history, and at-least-once. The project adds idempotency on `(job hash, revision)`, which the arbiter needs anyway |
| Artefacts | Content-addressed store. DVC remote on a tailnet host, or plain `rsync` to a hashed path. Workers pull inputs and push outputs by hash | No artefact is trusted by location. The receipt names hashes; the coordinator re-hashes on receipt |

A worker that joins needs: the tailnet, the tool it claims (`reentry doctor` tells it), and read access to the artefact store. It does not need the corpus, the Ghidra project, or any credential to the database.

## What "closed" means

- `reentry worker` exits 2 with `no pool configured: see docs/compute.md` unless `~/.config/reentry/pool.toml` is present and names a queue endpoint. With a pool file it exits 3: configured, loop not implemented.
- `reentry pool status` reports `closed` and the same hint.
- No network listener is started by any command in this repo.
- The job schema (`src/reentry/jobs.py`) defines `Job` and `Receipt` with hashed inputs and tool versions. That is the whole contract a remote worker would implement.

## What opening it will take

1. A `pool.toml`: tailnet hostname of the Temporal frontend, artefact store URL, which task queues this machine serves.
2. A Temporal dev server on one owner machine (`temporal server start-dev`), reachable only over the tailnet.
3. `reentry worker` turned from a refusal into a Temporal worker loop that calls the same local job runners `reentry` already uses.
4. Nothing else. No auth service, no certificate rotation, no dashboard.

## Rules that keep it honest

- A receipt from a remote worker is Advisory until the coordinator re-verifies the hashes. Re-running the proof is cheap compared to trusting it.
- Workers declare tool versions in every receipt. A version the owner's toolchain profile does not accept is rejected at the gate, not merged.
- The arbiter never runs remotely. One writer, on the machine that owns the corpus.
- Sharing is between people who already trust each other with a shell. The tailnet enforces who is in; the receipt discipline enforces what counts.

## What not to build

A hosted service. Accounts. A scheduler smarter than Temporal's queues. Encrypted artefact stores beyond what the tailnet already gives. Any of these turns a weekend seam into a thing with an on-call rota.
