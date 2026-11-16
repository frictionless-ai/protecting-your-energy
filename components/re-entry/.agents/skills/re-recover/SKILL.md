---
name: re-recover
description: Use this skill when asked for readable C or C++, a source bundle, a rebuildable function, or a .S fallback for a function or whole image. Apply even if the user only says "decompile this properly" or "make it compile". Routes between ReAgent candidates, rev.ng lifting and the compile-and-objdiff loop.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# re-recover

The target per function is readable C that compiles under the toolchain the original shipped with and matches the original bytes under objdiff. Everything short of that has a name, and the name is not "recovered".

## Order of attack

1. **Toolchain first.** Compiler family, version, optimization, ABI, struct packing. Calibrate against known-source functions (runtime library, SDK samples) compiled under candidate profiles and compared to shipped bytes. Wrong profile, nothing converges. Record the profile in `provenance.json`.
2. **Leaves before callers.** A known callee constrains its callers.
3. **Enrich before you decompile.** Boundaries, then types and structs, then names, then decompile. Pull what `re-match` already transferred from the donor build.
4. **Deterministic before creative.** Flag and pragma variation; mechanical transforms and known idioms; sibling knowledge; boundary and prototype repair. Only then a model rewrite.

## Candidate generators

| Need | Engine | What it gives |
|---|---|---|
| A C/C++ candidate with evidence gathered for you | ReAgent (`re-agent plan`, then `re-agent reverse`) | Reverser/checker loop over Ghidra context; its own build, test and structural gates; GREEN/YELLOW/RED parity |
| An LLVM IR lift of the function or image | rev.ng | IR you can read, transform or feed to Alive2 |
| Pseudocode to start from | REA `analyze_function` | Decompiler output with Evidence IDs |

ReAgent GREEN means ReAgent's gates passed. It is Advisory until this repo's compile-and-objdiff loop says otherwise. Give ReAgent the function, the matched sibling's recovered source if any, and the previous attempt's diff class. Take its candidate. Run the loop.

## The loop

Candidate, compiler under the recorded profile, object, objdiff against the original, classified result. Every candidate. Every change. Keep the exact compiler output and an attempt receipt: candidate hash, profile, timestamp, diff class.

Diff classes: compiler mismatch, type layout, calling convention, inlining, local shape, boundary error. The class picks the next move; a total difference count does not.

## When C is out of reach

Emit a `.S` that preserves the function's bytes and calling boundary. Header-label it as a fallback. It links the image and stays replaceable. It is Byte-authoritative, not source, and it never counts toward recovered C.

## C++

A parallel track. Recover it where RTTI, vtables, mangled names and compiler behaviour support it. A C-level byte match proves nothing about whether the original was C++.

## Refuse

- Presenting a `.S` as C.
- A ReAgent GREEN as objdiff parity.
- A compile without a comparison.
- Inferring C++ from a C match.
- A receipt from a previous run presented as this run's.
- Promoting on readability. Readable is the goal; it is not parity.

## Report

Per function: tier, profile, engine and version that produced the candidate, diff class if not Verified, receipt path. Then counts: Verified, Compiling, Advisory, `.S` fallback, with byte-accurate-C-plus-floor and max-C as two separate numbers. Rules in full: `../reverse-anything/references/rules.md`.
