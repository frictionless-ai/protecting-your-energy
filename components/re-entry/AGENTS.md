# AGENTS.md

You were pointed here to reverse a program, or a family of programs. Read this file, then `.agents/skills/reverse-anything/SKILL.md`. Everything else is reference.

## What you are doing

Recovering the software behind compiled builds, systematically, with proof. Not explaining one function. Not producing decompiler text. The product is a reconstruction whose relationship to the original bytes was checked, plus the artefacts that let someone rebuild or extend the program.

## Order of operations

1. Run `reentry doctor`. Know which engines are present before you plan around them.
2. Find existing work: a REA session, a Ghidra project with analysis, a corpus store, prior receipts. Reuse before you regenerate. An empty-looking view is not permission to analyze again.
3. Ingest and record provenance for every build before matching anything.
4. Match across builds. Transfer knowledge along matches. Keep confidence and origin on every transferred fact.
5. Recover readable C function by function. Compile after every change. Diff against the original with objdiff.
6. Export. Label every artefact with its claim tier.
7. Report what was verified, what was attempted, what was skipped. In that order, in those words.

## Claim tiers. Never blur them

| Tier | Meaning |
|---|---|
| **Verified** | Survived the hard proof named in its receipt: byte parity (compiled under the identified toolchain, objdiff zero-difference under rules R) or equivalence under stated semantics S for inputs in B. The receipt says which. Receipt on disk. |
| **Compiling** | Readable C that builds. Not shown to match. |
| **Advisory** | Decompiled, inferred, generated. Useful. Unproven. |
| **Context hint** | Names, notes, debug info, sibling-build knowledge. Witnesses, not facts. |
| **Byte-authoritative** | The original machine code, or a `.S` that preserves it. Not recovered source. |

A finished job is not a match. Compiling is not a match. A green label is not a match. A high similarity score is not an identity. Model confidence is not evidence. Byte-accurate C with an assembly floor and max-C are two counts; floor bytes never count toward recovered C.

## Rules that are not negotiable

- **No anonymous witness.** Every finding names the engine and version that produced it (BSim similarity, BinDiff graph match, VexIR2Vec embedding and objdiff parity mean different things). A normalized score with no engine is uninterpretable and cannot be replayed.
- **One writer per Ghidra program.** Ghidra transactions nest: a transaction opened while another is active on the same program joins it and shares its rollback. Serialize writes, or go through a store that records conflicts as conflicts.
- **Never re-analyze a program that already has analysis.** Open it and use what is there. Forced re-analysis only when the user asked for it in this conversation or the existing analysis is shown invalid. A reason you wrote yourself is not a request.
- **Never silently overwrite a contested finding.** If your proposed rename, type or match disagrees with what is recorded, record both with provenance. The arbiter decides, not the last writer.
- **Match is not proof.** Use matches to move names and compare code. Promote nothing on a match alone.
- **Compile continuously.** Every candidate: source, compiler, object, objdiff, classified result. Keep the exact compiler error and the attempt receipt.
- **C++ is parallel, not derived.** A C-level byte match says nothing about whether the original was C++. Recover C++ where RTTI, vtables and compiler behaviour support it. Do not infer it.
- **A `.S` fallback is scaffolding.** It keeps the image linking. It is not source and must stay replaceable.
- **Say "insufficient evidence".** When two explanations fit the bytes, say so and name what would separate them. Do not pick one and move on.
- **Reuse is labelled reuse.** A receipt you did not generate this run is reused evidence, not fresh.
- **Do not start servers, kill processes, or switch ports** to make room for your work. REA starts its own engines when an operation needs one; nothing else here does.
- **Shared compute is closed.** `reentry worker` and `reentry pool` refuse until a pool file exists. Do not open that path to finish a task; report that it would help.
- **Lawful targets only.** Your own software, software licensed for analysis, or authorized research.

## Finish line

The terminal claim for a binary is a fresh full-image compile plus an objdiff zero-difference receipt generated this run. Function-slice matches, historical receipts, assembly fallbacks, and the mere presence of source files do not substitute. If you cannot reach it, say how far you got in tier terms.

## Naming

| Kind | Form | Example |
|---|---|---|
| Local, global, parameter | `camelCase` | `slotIndex`, `gameState` |
| Type, class, struct name | `PascalCase` | `SaveGameHeader` |
| Struct field | `snake_case` | `save_version` |
| Enum constant | `SCREAMING_SNAKE` | `ITEM_TYPE_WEAPON` |

Prefer `slotIndex` to `local_8` when the role is clear. Leave it mangled when it isn't.

## Where things are

- Engine for single-target questions: REA, through its MCP server and its `reverse-engineer-anything` skill. Its rules for sessions, providers and Evidence IDs govern inside it.
- Candidates: ReAgent (`re-agent plan`, `re-agent reverse`, `re-agent doctor`). Its GREEN/YELLOW/RED parity gate is ReAgent's claim; objdiff parity is this repo's.
- This repo: the six skills in `.agents/skills/`, the curation in `docs/`, the entry CLI in `src/reentry/`. The tool catalogue of record is `src/reentry/tools.py`; `docs/stack.md` is prose about it.
