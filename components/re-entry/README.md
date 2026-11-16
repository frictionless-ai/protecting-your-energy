# re-entry

**Point an agent at this repo. It comes out the other side able to reverse a family of builds, with the proof rules already loaded.**

```
uvx --from git+https://github.com/bodencrouch/re-entry reentry setup
```

Nothing here is a new reverse-engineering engine. [REA](https://github.com/morluto/rea) already connects agents to Ghidra, Hopper, IDA, JavaScript, .NET, Android and firmware targets through one MCP server, and its `setup` already knows how to register itself with Claude Code, Codex, Cursor, Gemini CLI, OpenCode, Copilot CLI and the rest. `reentry setup` runs that, then adds what REA stops short of: a set of skills that treat several builds as one corpus, the proof contract that turns readable C into verified C, and a `doctor` that covers the whole bench, not one engine.

Then ask your agent:

```
Reverse ./builds/*. Match functions across the builds, carry names over,
and show me which functions you can prove, not just read.
```

## Why this exists

REA answers "how does this feature work" against one shipped artefact. The job here is bigger and more boring: take related builds of one program (Windows and Mac, 1.0 and 1.03, retail and debug) and recover the software behind all of them at once. Functions that correspond across builds share one identity. A name recovered on the build with symbols travels to the stripped one. Readable C gets written, compiled under the toolchain the original shipped with, and checked against the original bytes with [objdiff](https://github.com/encounter/objdiff). Where that isn't possible yet, the function ships as labelled assembly so the image still links.

The output is not decompiler text. It is a growing, evidence-backed reconstruction of a program family: source bundles, cross-build function maps, portable signatures, hook points for injection, WASM-ready code. Each has its own proof. None inherits another's.

That is the intended system. The status today is in [docs/status.md](docs/status.md): the skills and the entry CLI are the first thing built; the cross-build loop they describe is a design with named gaps, not a finished pipeline.

## What the stack is

Almost every practical gap already has a project that closes it. The missing piece was never another RE agent; it was a layer that keeps their evidence straight. So re-entry curates instead of reinventing, and adds only the glue in [docs/coordinator.md](docs/coordinator.md).

| Gap | Projects that close most of it | What stays open |
|---|---|---|
| Which function is which across builds | Ghidra BSim and Version Tracking, [BinDiff](https://github.com/google/bindiff), [VexIR2Vec](https://github.com/IITH-Compilers/VexIR2Vec); [BinKit 2.0](https://github.com/SoftSec-KAIST/BinKit) and [FIN](https://github.com/McGill-DMaS/FIN) to calibrate scores against ground truth | Split or merged functions, code that exists in one build only, ties the evidence cannot break |
| Running the original where it was meant to run | [PANDA](https://github.com/panda-re/panda), [avatar²](https://github.com/avatartwo/avatar2), [Renode](https://github.com/renode/renode), [Frida](https://github.com/frida/frida), real-hardware traces | Peripheral behaviour nobody modelled, exact timing |
| Is the recovered code actually the same code | objdiff byte parity, [AFL++](https://github.com/AFLplusplus/AFLplusplus), [angr](https://github.com/angr/angr), [Alive2](https://github.com/AliveToolkit/alive2), [VeriBin](https://github.com/purseclab/VeriBin), [CounterTV](https://github.com/compilerai/counter) | Proof coverage, side effects outside the function, semantics the solver can't model |
| Getting from pseudocode to code that builds | [ReAgent](https://github.com/Dryxio/reagent) candidates with its build and parity gates, [rev.ng](https://github.com/revng/revng) lifting | A candidate that passes ReAgent's gates is still not byte parity |
| Where did this fact come from | [DVC](https://github.com/iterative/dvc), [OpenLineage](https://github.com/OpenLineage/OpenLineage), [in-toto](https://github.com/in-toto/in-toto), [Sigstore cosign](https://github.com/sigstore/cosign) | A signed wrong answer is still wrong |
| Many agents, one database | Ghidra Server checkout, [Temporal](https://github.com/temporalio/temporal) for campaigns, [Dolt](https://github.com/dolthub/dolt) if branch merges turn out to be needed | Two conclusions that both fit the bytes need a human or more evidence, not a vote |

The full catalogue with install hints and the check `reentry doctor` runs for each is [docs/stack.md](docs/stack.md). Graphics-engine work keeps [RenderDoc](https://github.com/baldurk/renderdoc) and [apitrace](https://github.com/apitrace/apitrace) on the bench without making them a dependency; [STOKE](https://github.com/StanfordPL/stoke) is a reference, not a gate. Lending a friend your machine for a campaign is a closed seam, not a service: [docs/compute.md](docs/compute.md) says what it would take and why it stays small.

## How a run goes

1. **Ingest** every build and platform variant, plus any Ghidra project that already has analysis. Record exact provenance: hash, format, toolchain guess, where it came from.
2. **Analyze together.** One corpus, not N programs. Never re-run auto-analysis on a program that already has it.
3. **Match** with layered evidence: symbols and debug info first, then bytes and instruction shape, references, call-graph position, ABI, decompiler and P-code features. A match is a way to move and compare knowledge. It is not proof.
4. **Transfer** names, types, structures and findings along the matches, with confidence and origin attached. Ambiguous links stay ambiguous.
5. **Recover** per function: readable C that compiles under the identified toolchain and matches the original bytes under objdiff. If not yet: a `.S` that preserves the machine code and calling boundary, labelled as such, replaceable later.
6. **Verify** through the gate. Compile after every change. Keep the exact error and attempt receipt so a late failure doesn't cost the batch.
7. **Export** the bundle, the function map, the signatures, the hook data. Each with its own validation.
8. **Feed back.** Every new fact re-enters matching. Affected outputs regenerate.

The long version with the fallbacks is [docs/methodology.md](docs/methodology.md). What leaves the pipeline and what each artefact has to prove is [docs/deliverables.md](docs/deliverables.md).

## The skills

Six skills. One is the entry; five hide which engine does the work and refuse the shortcuts that would launder evidence.

| Skill | Use it when | Routes between |
|---|---|---|
| `reverse-anything` | You were handed a binary or a build family and need to start | REA's own skill for single-target work; `doctor`; the five below |
| `re-match` | "Where else is this function", carry names between builds | BSim, Version Tracking, BinDiff, VexIR2Vec; BinKit and FIN for calibration |
| `re-observe` | "What does it do when it runs" | PANDA, avatar², Renode, Frida, hardware traces |
| `re-recover` | Readable C or C++, a source bundle, a `.S` fallback | ReAgent candidates, rev.ng lifting, your own compile loop |
| `re-verify` | "Is this the same code" | objdiff, AFL++, angr, Alive2, CounterTV, VeriBin |
| `re-export` | Hand over bundles, maps, signatures, hook packs, receipts | DVC, OpenLineage, in-toto, cosign |

Every finding a skill produces names the engine and version that produced it. A finding with no named engine is not a finding.

## What you can't have

Four limits are not missing repos. They are the shape of the problem.

- Program equivalence is undecidable in general. Restricted classes prove under stated semantics; the rest get tests and fuzzing.
- Compilation erases names, types, boundaries, and the difference between source variants that compile identically. The original may not be unique.
- Hardware cannot be perfectly reproduced from a model. Renode's peripherals are functional, not physical.
- Two explanations can fit every observation. No confidence score manufactures the evidence that would separate them.

So completeness is always *against a target*: this program set, this platform set, this proof contract. An agent in this stack is allowed to answer "insufficient evidence". It is not allowed to invent certainty. [docs/limits.md](docs/limits.md) has the longer argument.

## Check readiness

```
reentry doctor
```

prints one line per engine: found, version, or the install hint. It runs `rea doctor` and `re-agent doctor` underneath and adds the rest of the bench. It installs nothing.

```
reentry setup --dry-run
```

shows every file REA and re-entry would write before either writes it.

## Repo map

- [AGENTS.md](AGENTS.md) is the rules an agent runs under here. Agents read this first.
- [.agents/skills/](.agents/skills/) holds the six skills. `skills/`, `.claude/skills/` and `.cursor/skills/` are generated stubs that point back here.
- [docs/methodology.md](docs/methodology.md) is the loop and its fallbacks.
- [docs/deliverables.md](docs/deliverables.md) is exports and their proof.
- [docs/coordinator.md](docs/coordinator.md) is the five pieces of new logic, and why only five.
- [docs/stack.md](docs/stack.md) is every tool, its job, its limit, its doctor check.
- [docs/limits.md](docs/limits.md) is what no tool fixes.
- [docs/compute.md](docs/compute.md) is shared compute: closed by default, the seam it would open through.
- [docs/agents.md](docs/agents.md) is what `setup` does per agent and how to do it by hand.
- [docs/status.md](docs/status.md) is what is implemented, what is curated, what is a claim.

## Lawful use

This is for software you are allowed to analyze: your own, licensed for it, or research with authorization. The tools here do not help with evading detection or attacking systems you don't own.

## License

MIT for this repo. Each listed project keeps its own license.
