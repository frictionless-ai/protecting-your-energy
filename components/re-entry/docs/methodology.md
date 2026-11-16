# Methodology

The loop is: ingest, prove provenance, analyze together, match, transfer, recover, verify, export, feed back. Each step has a fallback. The fallback lowers the claim tier; it never blanks the run.

## 1. Ingest

Take every build and platform variant you have. Take any Ghidra project that already carries analysis. Take debug builds, symbol files, PDBs, STABS, DWARF, map files, SDK headers, and source dumps if any exist.

Register each binary with: content hash, format, architecture, detected or suspected toolchain, origin (where the file came from and who vouches for it). Mark the build with the most debug information as the **donor**.

Fallback: a binary with no provenance still enters the corpus. It is tagged `provenance: unknown` and nothing recovered on it alone reaches Verified until the toolchain is identified.

## 2. Establish provenance

Toolchain identity is the global uncertainty that dominates everything local. Compiler family, version, optimization level, ABI, calling convention, struct packing. Get it wrong and no amount of per-function search converges.

Calibrate instead of guessing. Known-source functions (runtime library code, SDK samples) compile under candidate toolchain profiles; the objects compare to shipped functions. The best corpus-wide match is the profile. BinKit 2.0 (371,928 binaries across 8 architectures, 23 compilers and 6 optimization levels) is the reference for how much matching accuracy moves with the compiler. FIN labels which calls were inlined between two debug-bearing builds of the same program; those labels say how badly inlining will hurt your matcher before you run it. Both calibrate scores. Neither trusts them.

Fallback: when no profile matches, run with the closest two and record both. Recovery continues at Compiling tier; promotion waits.

## 3. Analyze together

One corpus. Ghidra auto-analysis runs once per program and is reused forever after. BSim ingests every program into one database so similarity queries span builds. REA sessions bind to one target at a time; keep one session per build and let the corpus store hold what connects them.

Fallback: a program that fails import or analysis is kept in the corpus as a `stub` with its triage-level facts (strings, imports, sections). It can still receive transferred names by address once a sibling is matched.

## 4. Match

Evidence layers, cheapest first, each one a separate witness:

1. Symbols and debug metadata: exact names when present.
2. Bytes and instruction structure: hash of normalized instructions, size, basic-block shape.
3. References: strings, constants, imports the function touches.
4. Call-graph position: who calls it, what it calls, where it sits.
5. ABI and prototype: parameter count, register usage, return type.
6. Decompiler and P-code features: BSim signatures, Version Tracking correlators, BinDiff graph matches, VexIR2Vec embeddings.

A match is **one-to-one, one-to-many, or many-to-one**. Inlining and outlining make the last two normal. The identity graph records all three with the witnesses that produced them.

A proposed match is a way to transfer and compare knowledge. It is not proof of identity. Confidence, engine and provenance ride with it.

Fallback: when witnesses disagree, the relationship is recorded as `contested` with every witness kept. Nothing transfers along a contested edge without an explicit decision.

## 5. Transfer

Move names, types, structures, comments, prototypes and recovered source along matches. Each transferred fact carries: source build, source function, match confidence, witnesses, and the transfer time. Field-level gates: a struct layout propagates only when access widths and offsets agree on both sides.

Fallback: a fact that fails its gate lands as a Context hint on the target. Visible, attributed, not applied.

## 6. Recover

Per function, the target is readable C that:

- compiles under the identified toolchain profile,
- matches the original function bytes under the project's objdiff rules.

Dependency order: call-graph leaves before callers. A known callee constrains its callers.

Enrich before you decompile: boundaries, then types and structures, then names, then decompile. Structure improves decompiler output; polishing bad pseudocode after the fact does not.

Deterministic methods before creative search:

1. Compiler flag, pragma and profile variation.
2. Mechanical source transforms and known idioms.
3. Propagated sibling knowledge from matched builds.
4. Structural correction (boundary, prototype, type layout).
5. Only then, a model rewrite. ReAgent's reverser/checker loop is the candidate generator here: give it the function, the target evidence and the diff shape, take its candidate, and run it through this repo's compile-and-objdiff gate. ReAgent's GREEN parity is ReAgent's claim about its own gates, not byte parity.

Classify every mismatch by diff shape: compiler mismatch, type layout, calling convention, inlining, local shape, boundary error. The class picks the next move.

Fallback: when C cannot reach parity in budget, export a `.S` that preserves the function's machine code and calling boundary. Label it. It links the image and keeps the function replaceable. It is Byte-authoritative, not recovered source.

C++: recover it where RTTI, vtables, mangled names and compiler behaviour support it, as a parallel track. A C-level match never implies the original was C.

## 7. Verify

Every candidate goes: source, compiler, object, objdiff, classified result. Compile after every change. Keep the exact compiler output and an attempt receipt (candidate hash, profile, timestamp, result). A late failure then costs one function, not the batch.

Beyond byte parity, when the question is behaviour rather than bytes:

- AFL++ differential fuzzing between original and recovered function.
- angr symbolic execution over the function pair.
- Alive2 for IR-level transformation validity; CounterTV for unoptimized LLVM IR against the x86-32 the compiler produced from it.
- VeriBin for patch-shaped changes between two binary versions.

Each produces PASS, FAIL or UNKNOWN with the exact conditions of the proof. UNKNOWN is an answer.

Fallback: a function with no verification path stays Compiling or Advisory. Its export says so.

## 8. Export

What leaves the pipeline is in [deliverables.md](deliverables.md). Each artefact is validated on its own. A generated hook description is not safe runtime behaviour. A source bundle is not a verified whole-image build.

## 9. Feed back

Every recovered fact re-enters matching. A newly verified function changes the call-graph constraints on its callers; a newly recovered struct changes access-width gates everywhere it is used. Affected outputs regenerate.

## Finish line

The terminal claim for a binary is a **fresh full-image compile and objdiff zero-difference receipt** produced in the current run. Function-slice matches do not substitute. Historical receipts do not substitute. Assembly fallbacks do not substitute. Source files on disk do not substitute.

None of the loop above is implemented end to end in this repo. The honest priority is therefore: make the skills route correctly, make `doctor` tell the truth about the bench, and close the proof gap, in that order. Not to claim the pipeline is complete.
