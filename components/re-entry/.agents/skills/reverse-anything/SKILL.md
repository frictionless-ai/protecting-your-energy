---
name: reverse-anything
description: Use this skill when asked to reverse, decompile, recover source from, match functions across, or explain a compiled program or a family of related builds. Apply even if the user only says "look at this exe", "what does this binary do", or "port this to the other build" without naming Ghidra, REA or objdiff. Routes to re-match, re-observe, re-recover, re-verify and re-export.
license: MIT
metadata:
  author: re-entry
  version: "0.1"
---

# reverse-anything

You are reversing a program, or several related builds of one. REA is the engine for single-target questions; this skill set is for the corpus: which function is which across builds, what carries over, what can be proven.

## Before touching the binary

1. Run `reentry doctor`. Know what is present. Plan around what is, not what should be. Do not run `rea setup` or `reentry setup` before every task; see [references/connect-only-when-needed.md](references/connect-only-when-needed.md).
2. Look for existing state: an open REA session (`binary_session` with `{}`), a Ghidra project with analysis, a corpus store, receipts. Reuse is the default. Regenerating needs a reason you can quote.
3. Decide the question type and hand off:

| Question | Skill |
|---|---|
| What is in this file, what does this function do, how does this feature work | REA's own `reverse-engineer-anything` skill, directly |
| Where else is this function; carry names, types, structs between builds | `re-match` |
| What does it do when it runs | `re-observe` |
| Give me readable C, a source bundle, a `.S` fallback | `re-recover` |
| Is this the same code; prove parity or equivalence | `re-verify` |
| Hand over bundles, maps, signatures, hook packs, receipts | `re-export` |

Pick the cheapest tier that answers. Strings and imports before decompilation. Decompilation before execution. Execution before proof.

## Claim tiers

Five, and they never blur:

- **Verified**: survived the hard proof named in its receipt (objdiff byte parity under rules R, or equivalence under semantics S for inputs in B). Receipt on disk.
- **Compiling**: builds. Not shown to match.
- **Advisory**: decompiled, inferred, generated. Useful. Unproven.
- **Context hint**: names, notes, debug info, sibling-build knowledge. Witnesses.
- **Byte-authoritative**: original bytes or a `.S` preserving them. Not source.

A finished job is not a match. A compile is not a match. A score is not an identity. The full rule list is [references/rules.md](references/rules.md).

## Working

- No anonymous witness. Every finding names the engine and version that produced it: "renamed `loadSave` from the debug build via BSim 0.91 (Ghidra 12.0) and call-graph agreement", not "renamed `loadSave`".
- Never re-run auto-analysis on a program that already has it.
- One writer per Ghidra program. Propose; do not race another writer.
- When two readings fit the bytes, record both and name the observation that would separate them. Do not pick.
- Never start servers, kill processes or change ports to make room. REA starts its own engines when an operation needs them.

## Reporting

In this order, in these words: **verified**, **attempted**, **skipped**. Tier counts come from receipts, not from job status. Say "insufficient evidence" when it is true.

## Additional resources

- [references/rules.md](references/rules.md): claim tiers and the non-negotiable rules, complete.
- [references/connect-only-when-needed.md](references/connect-only-when-needed.md): when setup and doctor are the right move and when they are noise.
- [references/agent-paths.md](references/agent-paths.md): where each agent keeps MCP config and skills, for manual repair.
