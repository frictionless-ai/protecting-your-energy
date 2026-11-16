# Deliverables

A list of matched functions is not the product. The product is a per-binary source bundle plus separate exports, each with its own proof. Nothing inherits another artefact's validation.

## Per-binary source bundle

```
<binary>/
  src/                 recovered C (and C++ where supported), one file per module or function
  asm/                 .S fallbacks, one per function not yet recovered, each header-labelled
  include/             recovered types, structures, enums, prototypes
  function-map.json    address, logical_id, source location, tier
  identity.json        cross-build correspondences with witnesses and confidence
  provenance.json      binary hash, toolchain profile, Ghidra project ref, tool versions
  signatures/          portable patterns that find each function without a fixed address
  receipts/
    compile/           per-function compiler output and attempt record
    objdiff/           per-function comparison result and diff class
    image/             whole-image compile + objdiff receipt when one exists
  BUNDLE.md            coverage by tier; byte-accurate C with assembly floor and max-C counted
                       separately; what is missing; what is contested
```

Validation: every file under `src/` has a compile receipt. Every function claimed Verified has an objdiff receipt with zero differences under the stated rules. `BUNDLE.md` reports tier counts from receipts, not from job status. Floor bytes never count toward recovered C.

Claim: a bundle is a **source bundle**. It is not a verified whole-image build unless `receipts/image/` holds a fresh one.

## Cross-binary function map

`identity.json` and `function-map.json` across the corpus. Records one-to-one, one-to-many and many-to-one relationships. Keeps contested links as contested.

Validation: every edge lists its witnesses with engine and version. No edge without at least one.

Claim: identity is a `logical_id`, not an address. An address is one build's instance.

## Portable signatures

Patterns (masked byte sequences, structural hashes, BSim signatures) that locate a function in a build it was not derived from.

Validation: each signature is tested against every build in the corpus. The export records hit, miss, and false-positive counts per build.

Claim: a signature finding a function is a **location**, not an identity. The identity graph decides identity.

## Hook pack

Codecave and hook locations, calling convention, parameter layout, and what the function expects on entry, for DLL or shared-library injection and modding.

Validation: resolution (the address exists in that build), installation (the hook can be written), call (typed call succeeds), observed behaviour (the original did what the hook expected). Four separate gates. Pass one, you have passed one.

Claim: a hook description is **data**. It is not safe runtime behaviour until the four gates pass in the target build.

## WASM-ready code and integration artefacts

Recovered source selected and shimmed for a WASM build, with the integration glue.

Validation: builds under the WASM toolchain, and the function-level test set from the native recovery passes against it.

Claim: WASM parity is a **different proof** from native byte parity. Verified native does not make Verified WASM.

## Lua-facing interfaces

Where a runtime exposes scripting, the typed interface a script sees: function names, parameter types, return types, with the native function they bind to.

Validation: each binding resolves to a function in the identity graph and its prototype matches the recovered one.

Claim: an interface file is a **contract description**. Behaviour is the native function's claim, not the binding's.

## Receipts

Every receipt is immutable, names its inputs by hash, names the tool versions, and is signed when cosign is configured. Signing proves who produced it and that it was not altered. It does not prove the conclusion is right.

## What never ships as recovered source

- Copied bytes.
- A `.S` fallback presented as C.
- Decompiler output with names fixed and no compile receipt.
- A generated candidate that compiled but was never compared.
- A ReAgent GREEN result presented as objdiff parity.
- Anything whose receipt was produced by a previous run and is presented as this run's.
