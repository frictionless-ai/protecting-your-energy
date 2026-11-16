# The coordinator

Every engine in [stack.md](stack.md) exists already. What does not exist is the layer that keeps their evidence straight across many agents and many builds. That layer needs five pieces of new logic. Everything else is delegation.

```
Agents (planner, worker, critic, aggregator)
        | hypotheses, candidates, questions
        v
+-----------------------------------------------------------+
| Coordinator                                               |
|  identity graph . evidence contract . validation gate     |
|  conflict arbiter . capability router                     |
+-------+-----------+-----------+-----------+---------------+
        v           v           v           v
   Matching     Execution   Verification  Recovery
   BSim, VT     PANDA       objdiff       ReAgent
   BinDiff      Frida       AFL++, angr   rev.ng
   VexIR2Vec    Renode      Alive2        REA (targets)
                avatar2     VeriBin
                            CounterTV
        |           |           |           |
        +-----------+-----+-----+-----------+
                          v
   Versioned evidence: SQLite store, DVC, Temporal, OpenLineage, in-toto, cosign
                          v
   Guarded Ghidra commits + exports with claim tiers
```

## 1. Identity graph

Nodes are concrete functions (build, address, size, hash). Edges are correspondences: one-to-one, one-to-many, many-to-one. Each edge carries its witnesses (which engine and version, what score, which evidence layer), a confidence, and a status: `proposed`, `accepted`, `contested`, `rejected`. A `logical_id` names a connected component the arbiter has accepted.

Why it is new: BSim, BinDiff and VexIR2Vec each return pairs with scores. Ghidra Version Tracking keeps Accepted and Rejected per pairwise match, but it is two-program only. None of them stores competing hypotheses across a corpus, models inlining as a graph relationship, or keeps a rejected pair as a record. The graph does.

Store: a SQLite schema shipped with this repo. Dolt only if per-agent branch merges are measured to be needed; it records row-level conflicts the arbiter could read, at the cost of running a server. Ghidra Server is file-level checkout over RMI and is not a candidate for the graph.

## 2. Evidence contract

Every finding is a record with immutable references: binary hashes, trace ids, engine names and versions, generated-source hash, validation results, and the parent findings it depends on. OpenLineage carries the job/input/output relationships. in-toto attests who ran what. cosign signs the result.

Why it is new: the engines emit results, not records. Making the record mandatory is a schema and a refusal: the gate will not read a finding without one.

## 3. Validation gate

A hypothesis becomes a Verified finding only after the checks configured for its kind have run. Byte parity for recovered source: compile plus objdiff. Behavioural equivalence: AFL++ differential, angr, Alive2 or CounterTV as applicable. Patch safety: VeriBin. Each check records PASS, FAIL or UNKNOWN and the exact conditions (inputs, bounds, semantics assumed). The receipt names which proof was run; the Verified tier means nothing without it.

UNKNOWN is a first-class result. The gate never converts it to PASS because nothing failed.

## 4. Conflict arbiter

Every proposed change carries the database revision it was derived from. If the current revision differs, the arbiter compares the proposal against what changed. Compatible: apply. Incompatible: record both as `contested`, with provenance, and queue for resolution. Silent overwrite is not an outcome the arbiter can produce.

Resolution is by named check: which evidence would separate the two? Run it if it can run. Otherwise the conflict stays visible and both interpretations are exported as contested. A vote is not a resolution.

Ghidra specifics: Ghidra transactions nest; a transaction started while another is open on the same program joins it and shares its rollback (`DomainObject.endTransaction(id, false)` rolls back every concurrent transaction). So the arbiter is the only writer to a live program. Agents propose to the arbiter; the arbiter commits in serialized transactions.

## 5. Capability router

Given a binary format, architecture, question, cost budget and required evidence tier, pick the engine. REA for "what is in this file" and "what does this function do". BSim, BinDiff or VexIR2Vec for "where else is this function". PANDA or Frida for "what does it do when it runs". ReAgent for "give me a candidate that builds". objdiff for "is this C the same code". AFL++ or angr when bytes cannot match but behaviour must.

Why it is new: nothing else knows all the engines' preconditions (Renode needs a platform description, VeriBin needs two versions, CounterTV needs the LLVM IR the x86 came from). The router does, and it declines with a reason rather than running the wrong tool.

The decision half of the router is prose in the skills: an agent reads the question and the `doctor` output and picks. The deterministic half is `reentry doctor --json`: what is installed, which preconditions hold. Neither half probes binaries on its own.

The router also decides *where* a job runs. Today the only answer is "here". When [compute.md](compute.md) opens, the answer becomes a task queue name and the worker that serves it; the router's inputs do not change.

## Workflow engine

Temporal runs the campaigns: thousands of compile-and-diff attempts, retried, resumable, with execution history. Activities may run more than once, so every write goes through the arbiter and is idempotent on (finding hash, revision).

## What the coordinator does not do

It does not decide which of two contested interpretations is true. It does not raise a claim tier because a job finished. It does not synthesize source. Those are agents' and engines' jobs, and the coordinator exists to make sure their outputs are kept honest, not to replace them.
