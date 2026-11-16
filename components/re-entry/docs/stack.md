# Stack

Every tool, its job, its limit, and the check `reentry doctor` runs. The catalogue of record is `src/reentry/tools.py`; this file explains it. If the two disagree, the code is wrong or this is stale. Fix one, do not keep both.

Layers: **core** is required for the recovery loop. **matching**, **calibration**, **execution**, **verification**, **recovery** are engines the router picks between. **evidence** and **concurrency** are the coordinator's substrate. **bench** is kept for specific jobs and never a dependency.

## Core

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| [REA](https://github.com/morluto/rea) | One MCP server over native, managed, JavaScript, Android and firmware targets; registers itself with every supported agent; Evidence IDs on every result | One target per session; answers single-artefact questions, not corpus ones | `rea doctor --json`, or `npx -y rea-agents@latest doctor --json` |
| [Ghidra](https://github.com/NationalSecurityAgency/ghidra) | Analysis, decompilation, P-code, BSim, Version Tracking | Transactions nest; one writer per program | `$GHIDRA_INSTALL_DIR/support/analyzeHeadless` exists |
| [objdiff](https://github.com/encounter/objdiff) | Object-level byte comparison; the proof for Verified | Compares objects, not behaviour | `objdiff-cli --version` |
| Toolchain of the target | The compiler the original shipped with (MSVC under Wine, old GCC, console SDKs) | Must be identified by calibration, not guessed | Project-specific; doctor reports the configured profile's compiler path |
| [uv](https://github.com/astral-sh/uv) | Runs this repo | none | `uv --version` |
| Node.js and npm | Runs REA | REA needs Node 22.19+, 24.11+ or 26+ | `node --version` |

## Matching

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| Ghidra BSim | Decompiler-feature similarity across a repository of programs | Needs a database created and every program ingested first; empty results often mean that step never ran | `$GHIDRA_INSTALL_DIR/support/bsim` exists |
| Ghidra Version Tracking | Pairwise correlators (exact bytes, symbol names, function references) with Accepted and Rejected per match | Two programs at a time | `analyzeHeadless` exists (VT ships with Ghidra) |
| [BinDiff](https://github.com/google/bindiff) | Call-graph and flow-graph diffing between two binaries | Pairwise; no corpus notion | `bindiff --version` |
| [VexIR2Vec](https://github.com/IITH-Compilers/VexIR2Vec) | Architecture-neutral function embeddings over VEX IR | Embedding similarity is a hint, never identity | Python import `vexir2vec` |

## Calibration

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| [BinKit 2.0](https://github.com/SoftSec-KAIST/BinKit) | Ground truth: 371,928 binaries, 8 architectures, 23 compilers, 6 optimization levels. Says how matcher scores move with the compiler | GNU packages only; no proprietary compilers | Dataset directory configured |
| [FIN](https://github.com/McGill-DMaS/FIN) | Labels which calls in one debug-bearing ELF build were inlined in another, by comparing DWARF. Ground truth for how inlining hurts a matcher | Needs IDA Pro (`--ida`), ELF, debug info in both builds. A dataset builder, not a matcher for stripped binaries | checkout path and configured IDA path |

## Execution

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| [PANDA](https://github.com/panda-re/panda) | Whole-system record and replay, taint, introspection | Models what QEMU models | Python import `pandare` |
| [avatar²](https://github.com/avatartwo/avatar2) | Orchestrates emulators and real hardware in one execution | Hardware side does not scale | Python import `avatar2` |
| [Renode](https://github.com/renode/renode) | Embedded platform simulation with peripheral models | Peripherals are functional, not physical | `renode --version` |
| [Frida](https://github.com/frida/frida) | Dynamic instrumentation of live processes | Observes; does not prove | `frida --version` |
| Real-hardware traces | Ground truth for timing and undocumented behaviour | Manual; one device at a time | configured trace directory |

## Verification

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| [AFL++](https://github.com/AFLplusplus/AFLplusplus) | Differential fuzzing original vs recovered | Finds differences; cannot prove absence | `afl-fuzz --version` |
| [angr](https://github.com/angr/angr) | Symbolic execution over function pairs | Path explosion; external effects unmodelled | Python import `angr` |
| [Alive2](https://github.com/AliveToolkit/alive2) | Validates LLVM IR transformations under LLVM semantics | IR only; LLVM semantics only | `alive-tv --version` |
| [CounterTV](https://github.com/compilerai/counter) | Translation validation: unoptimized LLVM IR against the x86-32 the compiler produced from it, by counterexample-guided correlation | x86-32 only; needs the source's IR; OOPSLA'20 Docker artefact with one commit (2020), 32 GiB RAM recommended | Docker image `oopsla20-ctv` present, or checkout path |
| [VeriBin](https://github.com/purseclab/VeriBin) | Binary-level patch safety via symbolic execution (NDSS'25) | Patch-shaped changes, not whole-program equivalence | checkout path |

## Recovery

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| [ReAgent](https://github.com/Dryxio/reagent) | Reverser/checker model loop over Ghidra context that emits C/C++ candidates, with build, test and structural gates and a GREEN/YELLOW/RED parity verdict | Its own gates are conservative verification, not byte parity; candidates still go through objdiff here | `re-agent doctor` |
| [rev.ng](https://github.com/revng/revng) | Lifting to LLVM IR and decompilation | Alternative lifter; outputs are Advisory | `revng --version` |

## Evidence

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| SQLite (stdlib) | Identity graph and findings store shipped with this repo | Single writer; no branch merges | always present |
| [Temporal](https://github.com/temporalio/temporal) | Durable campaigns, retries, execution history; the job queue shared compute would use | Activities can run twice; writes must be idempotent | `temporal --version` |
| [DVC](https://github.com/iterative/dvc) | Content-addressed artefact storage and pipelines | Storage, not meaning | `dvc version` |
| [OpenLineage](https://github.com/OpenLineage/OpenLineage) | Job/input/output lineage records | Describes runs; does not judge findings | Python import `openlineage` |
| [in-toto](https://github.com/in-toto/in-toto) | Attestations of who ran what on which inputs | Attests process, not correctness | `in-toto-run --version` |
| [cosign](https://github.com/sigstore/cosign) | Signs receipts and attestations | A signed wrong answer is still wrong | `cosign version` |
| [Dolt](https://github.com/dolthub/dolt) | Versioned SQL with branches and row-level merge conflicts, if per-agent branching is measured to be needed | Records conflicts; does not resolve them; runs a server | `dolt version` |

## Concurrency

| Tool | Job | Limit | Doctor check |
|---|---|---|---|
| Ghidra Server | Shared repository with checkout and checkin per program | RMI over SSL; checkout is per file, not per function | configured host:port reachable |

## Bench

Not installed by default. Used for a specific job, then put back. Doctor reports these as `bench` and does not probe them.

| Tool | When | Why not a dependency |
|---|---|---|
| [ghidra-rpc](https://github.com/cellebrite-labs/ghidra-rpc) | A persistent PyGhidra daemon per `.gpr` with a JSON CLI; autosaves after every command; can write raw bytes | One program state per daemon. Never start it against a project another writer has open |
| [RenderDoc](https://github.com/baldurk/renderdoc) | Graphics engines: frame, shader, resource, draw-call capture | No D3D9/D3D10 or legacy OpenGL compatibility profile |
| [apitrace](https://github.com/apitrace/apitrace) | Older graphics APIs RenderDoc skips | Tracing, not analysis |
| [STOKE](https://github.com/StanfordPL/stoke) | x86-64 instruction-level equivalence and synthesis, as a reference | Research prototype, no active development, per its maintainers |
| [SBridge](https://dl.acm.org/doi/10.1145/3797090) | Source-to-binary function similarity by control-block matching; 75.13% recall@1 on 3,904 BinKit binaries with about 40% inlined functions (FSE'26) | No public artefact located |
| [O2NMatcher](https://github.com/island255/binary2source-matching-under-function-inlining) | Source function sets for binary-to-source matching under inlining | Research code |
| [vSim](https://www.ndss-symposium.org/ndss-paper/vsim-semantics-aware-value-extraction-for-efficient-binary-code-similarity-analysis/) | Semantic-value similarity, for benchmark comparison | Adopt only if it beats current matchers on an independent corpus |
| Co2FuLL | LLM-verified binary similarity, for benchmark comparison | Same bar as vSim |

## Adding a tool

Add it to `src/reentry/tools.py` with a layer, a one-line job, a one-line limit, and a detect spec that resolves when present. Then add its row here. A tool without a limit column entry is not understood well enough to add.
