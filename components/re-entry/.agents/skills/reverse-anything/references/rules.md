# Rules

The complete list. The skill bodies quote the parts they need; this is the whole thing.

## Claim tiers

| Tier | Meaning |
|---|---|
| **Verified** | Survived the hard proof named in its receipt: byte parity (compiled under the identified toolchain, objdiff zero-difference under rules R) or equivalence under stated semantics S for inputs in B. The receipt says which. Receipt on disk. |
| **Compiling** | Readable C that builds. Not shown to match. |
| **Advisory** | Decompiled, inferred, generated. Useful. Unproven. |
| **Context hint** | Names, notes, debug info, sibling-build knowledge. Witnesses, not facts. |
| **Byte-authoritative** | The original machine code, or a `.S` that preserves it. Not recovered source. |

Byte-accurate C with an assembly floor and max-C are two counts. Floor bytes never count toward recovered C.

## Non-negotiable

- **No anonymous witness.** Every finding names the engine and version that produced it. BSim similarity, Version Tracking correlators, BinDiff graph matches, VexIR2Vec embeddings and objdiff parity mean different things; a score without its engine cannot be interpreted or replayed.
- **One writer per Ghidra program.** Ghidra transactions nest. A transaction opened while another is active on the same program joins it and shares its rollback. Serialize writes or go through a store that records conflicts as conflicts.
- **Never re-analyze a program that already has analysis.** Forced re-analysis only when the user asked for it in this conversation or the existing analysis is shown invalid. A reason you wrote yourself is not a request.
- **Never silently overwrite a contested finding.** Record both with provenance.
- **Match is not proof.** Use matches to move names and compare code. Promote nothing on a match alone.
- **Compile continuously.** Source, compiler, object, objdiff, classified result. Keep the exact compiler error and the attempt receipt.
- **C++ is parallel, not derived.** A C-level byte match says nothing about whether the original was C++.
- **A `.S` fallback is scaffolding.** It links the image. It is not source. It stays replaceable.
- **Say "insufficient evidence".** Name what would separate the candidates. Do not pick.
- **Reuse is labelled reuse.** A receipt from a previous run is reused evidence, not fresh.
- **Do not start servers, kill processes or switch ports.** REA starts its own engines on demand; nothing else here does.
- **Shared compute is closed.** Do not open it to finish a task; report that it would help.
- **Lawful targets only.**

## Finish line

A fresh full-image compile plus an objdiff zero-difference receipt generated this run. Function-slice matches, historical receipts, assembly fallbacks and source files on disk do not substitute.

## Naming

| Kind | Form | Example |
|---|---|---|
| Local, global, parameter | `camelCase` | `slotIndex` |
| Type, class, struct | `PascalCase` | `SaveGameHeader` |
| Struct field | `snake_case` | `save_version` |
| Enum constant | `SCREAMING_SNAKE` | `ITEM_TYPE_WEAPON` |
