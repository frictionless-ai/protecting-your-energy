---
name: re-match
description: Use this skill when asked where else a function appears, to match or diff functions across builds or platform variants, or to carry names, types and structures from one build to another. Apply even if the user only says "this is the same game on Mac" or "port the symbols over". Routes between BSim, Version Tracking, BinDiff and VexIR2Vec; calibrates with BinKit and FIN.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# re-match

A match is a way to move and compare knowledge between builds. It is not proof that two functions are the same function. Everything below exists to keep that distinction.

## Pick the engine

Read `reentry doctor --json` first. Then:

| Situation | Engine | Why |
|---|---|---|
| Both builds in one Ghidra project or BSim database | Ghidra BSim | Decompiler-feature similarity across many programs at once |
| Exactly two programs, want Accepted/Rejected per pair kept | Ghidra Version Tracking | Correlators for exact bytes, symbols, references; the session records your decisions |
| Two binaries, graph structure matters, no Ghidra project | BinDiff | Call-graph and flow-graph matching |
| Different architectures | VexIR2Vec | Embeddings over VEX IR are architecture-neutral; similarity is a hint |

Run more than one when you can. Each is a separate witness. Agreement raises confidence; disagreement is a `contested` edge, not a tie-break.

## Layer the evidence

Cheapest first, each layer recorded on its own:

1. Symbols and debug metadata.
2. Normalized instruction hash, size, basic-block shape.
3. Strings, constants and imports the function touches.
4. Call-graph position.
5. Prototype and ABI.
6. Decompiler and P-code features (the engines above).

An edge is one-to-one, one-to-many or many-to-one. Inlining and outlining make the last two normal. Record the shape; do not force a pair.

## Calibrate before you trust a score

A BSim 0.9 and a BinDiff 0.9 are not the same claim. Before promoting any threshold:

- BinKit 2.0 tells you how your matcher's scores move across 23 compilers and 6 optimization levels on known-identical functions. Run your matcher on a BinKit slice that resembles your target's toolchain and read the distribution.
- FIN tells you how much inlining to expect: given two debug-bearing ELF builds, it labels which call sites were inlined. If your donor build has DWARF, run it and expect that fraction of one-to-many edges.

Neither tool matches your target. They tell you how much to believe the one that does.

## Transfer

Along an `accepted` edge only. Each transferred fact carries source build, source function, engine and version, score, and transfer time. Field-level gates: a struct layout crosses only when access widths and offsets agree on both sides; a prototype crosses only when the ABI matches.

A fact that fails its gate lands on the target as a Context hint: visible, attributed, not applied.

## Refuse

- Promoting identity on a score alone.
- Transferring across a `contested` or `proposed` edge.
- Reporting a function matched when it exists in one build only.
- A normalized score with no engine name.
- Running FIN or BinKit as if they were matchers.

## Report

Per edge: builds, addresses, shape (1:1, 1:N, N:1), status, witnesses with engine and version and score, what transferred, what was gated. Then: how many edges are `contested` and which observation would settle each. Rules in full: `../reverse-anything/references/rules.md`.
