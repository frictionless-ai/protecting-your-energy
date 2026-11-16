# Status

Three categories. Do not move an item between them without the evidence that moves it.

## Implemented and observed

Nothing yet. This section fills as commits land with their verification output.

## Curated, not integrated

Each of these was checked against its public documentation. None has been wired to the coordinator or benchmarked in combination here.

- Core: REA, Ghidra, objdiff.
- Matching: BSim, Version Tracking, BinDiff, VexIR2Vec.
- Calibration: BinKit 2.0, FIN.
- Execution: PANDA, avatar², Renode, Frida.
- Verification: AFL++, angr, Alive2, VeriBin, CounterTV.
- Recovery: ReAgent, rev.ng.
- Evidence: Temporal, OpenLineage, in-toto, DVC, cosign, Dolt (conditional).
- Concurrency: Ghidra Server.
- Bench only: ghidra-rpc, RenderDoc, apitrace, STOKE, SBridge, O2NMatcher, vSim, Co2FuLL.

## Claimed, not implemented

- The six skills in `.agents/skills/` and the stubs that point at them.
- `reentry setup`, `reentry doctor`, `reentry tools`: designed in README and docs/agents.md. No code, no observed run.
- The coordinator's five pieces ([coordinator.md](coordinator.md)). Design only.
- The cross-build recovery loop ([methodology.md](methodology.md)). Design only.
- The fresh whole-image compile and objdiff zero-difference receipt. Not reached for any binary.
- Shared compute ([compute.md](compute.md)). Only the refusal path and the `Job`/`Receipt` schema are planned.

## What moves an item

- Curated to Implemented: a command in this repo invokes it, and a receipt from that invocation exists.
- Claimed to Implemented: the code exists, and one run produced the artefact it claims to produce, observed this run.
