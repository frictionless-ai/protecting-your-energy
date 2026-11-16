---
name: re-export
description: Use this skill when asked to export, package, sign, attest or hand over a source bundle, cross-build function map, portable signatures, hook pack, WASM artefacts, Lua interfaces or receipts. Apply even if the user only says "give me the output" or "ship it". Routes between DVC, OpenLineage, in-toto and cosign.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# re-export

What leaves the pipeline is a set of artefacts, each with its own proof. None inherits another's. An export that cannot show its receipts is not ready.

## The artefacts

| Artefact | Validation it must carry | What it is not |
|---|---|---|
| Source bundle (`src/`, `asm/`, `include/`, `function-map.json`, `identity.json`, `provenance.json`, `receipts/`, `BUNDLE.md`) | Every `src/` file has a compile receipt; every Verified function has an objdiff receipt | A verified whole-image build, unless `receipts/image/` holds a fresh one |
| Cross-build function map | Every edge lists witnesses with engine and version | Identity by address. Identity is `logical_id` |
| Portable signatures | Tested against every build; hit, miss, false-positive counts per build | Identity. A signature finding a function is a location |
| Hook pack | Four gates per hook: resolves, installs, calls, observed behaviour | Safe runtime behaviour until all four pass in the target build |
| WASM artefacts | Builds under the WASM toolchain; native function-level tests pass against it | Native parity. Different proof |
| Lua interfaces | Each binding resolves in the identity graph; prototype matches recovered | Behaviour. That is the native function's claim |

`BUNDLE.md` counts tiers from receipts, not from job status. Byte-accurate C with assembly floor and max-C are two numbers. Floor bytes never count toward recovered C.

## Provenance

| Need | Tool |
|---|---|
| Store artefacts by content hash, move them between machines | DVC |
| Record which job consumed which inputs and produced which outputs | OpenLineage |
| Attest who ran what, on which inputs, with which tool versions | in-toto |
| Sign receipts and attestations so tampering is detectable | cosign |

Signing proves who produced a record and that it was not altered. It does not prove the conclusion is right. Say that in the bundle.

## Before export

1. `reentry doctor --json`: are the signing and lineage tools present? If not, export unsigned and say so in `BUNDLE.md`. Do not skip the export; lower its claim.
2. Walk `receipts/`. Every claim in `function-map.json` has a receipt or the tier drops until it does.
3. Reused receipts are labelled reused, with the run they came from.
4. Contested edges are exported as contested, with both interpretations and the observation that would settle them.

## Refuse

- An artefact without its own receipt.
- A prior run's receipt presented as this run's.
- Tier counts from job status.
- A hook pack described as safe.
- A WASM build described as Verified because the native was.
- Silently dropping a contested finding to make the map look clean.

## Report

What was exported, where, with which receipts; what was exported unsigned and why; what was withheld and what it needs. Rules in full: `../reverse-anything/references/rules.md`.
