---
name: re-verify
description: Use this skill when asked whether recovered code is the same as the original, to prove byte parity, behavioural equivalence or patch safety, or to decide whether a function may be called Verified. Routes between objdiff, AFL++, angr, Alive2, CounterTV and VeriBin.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# re-verify

Verified means one thing: the hard proof named in the receipt was run and passed. There are two kinds of proof here and they are not interchangeable. Say which one you ran.

## Byte parity

The default and the strongest. Compile the candidate under the recorded toolchain profile, compare the object to the original with objdiff, require zero differences under the project's rules R (which relocations are masked, which sections compared). Receipt: candidate hash, profile, objdiff version, rules, result, diff class on failure.

This proves the candidate *produces* the original. It does not prove it *is* the author's text; see the limits doc in the repo.

## Behavioural equivalence

When bytes cannot match (different compiler available, or the question is about behaviour, not bytes), pick by what you have:

| Have | Engine | Proves |
|---|---|---|
| Two runnable functions and a harness | AFL++ differential fuzzing | Finds differences on inputs it reached. Never proves absence |
| Two functions, symbolic inputs, bounded paths | angr | Equivalence over the explored paths under angr's memory model |
| LLVM IR before and after a transformation | Alive2 | Refinement under LLVM semantics |
| Unoptimized LLVM IR and the x86-32 the compiler emitted from it | CounterTV | Translation validity by counterexample-guided correlation. x86-32 only; needs the source's IR |
| Two versions of one binary, a patch between them | VeriBin | The patch did not introduce the modelled class of unsafe behaviour. Patch-shaped, not whole-program |

Every result is PASS, FAIL or UNKNOWN with the exact conditions: semantics S assumed, input bounds B, paths explored, time budget. UNKNOWN is a result. It never becomes PASS because nothing failed.

Receipt: engine and version, inputs by hash, conditions, result. "Equivalent under angr for inputs in [0, 2^16) over 412 paths" is a claim. "Equivalent" is not.

## Check preconditions with doctor

`reentry doctor --json` says which engines are present. CounterTV needs its Docker artefact; Alive2 needs `alive-tv`; AFL++ needs a harness you wrote. Decline with the missing precondition named rather than substituting a weaker engine silently.

## Whole image

The finish line for a binary is a fresh full-image compile and an objdiff zero-difference receipt generated this run. Per-function receipts, old image receipts, and `.S` fallbacks linked in do not substitute. If the image does not reach it, report the tier counts and stop.

## Refuse

- UNKNOWN reported as PASS.
- "Equivalent" without semantics and bounds.
- A compile as a match.
- A ReAgent GREEN, a fuzz run with no findings, or a high similarity score as Verified.
- Re-labelling a historical receipt as fresh.

## Report

Per function: proof kind, engine and version, conditions, result, receipt path. Then: Verified count by proof kind, UNKNOWN count with reasons, and what would turn each UNKNOWN into an answer. Rules in full: `../reverse-anything/references/rules.md`.
