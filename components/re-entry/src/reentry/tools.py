from __future__ import annotations

import argparse
from dataclasses import dataclass

from .cli import register

LAYERS = (
    "core", "matching", "calibration", "execution", "verification",
    "recovery", "evidence", "concurrency", "bench",
)


@dataclass(frozen=True)
class Tool:
    name: str
    layer: str
    job: str
    limit: str
    detect: str | None
    doctor_text: str
    install_hint: str
    url: str | None


_GH = "https://github.com/"
_BSIM = "env:GHIDRA_INSTALL_DIR/support/bsim"
_HEADLESS = "env:GHIDRA_INSTALL_DIR/support/analyzeHeadless"

TOOLS: tuple[Tool, ...] = (
    Tool("REA", "core",
         "One MCP server over native, managed, JavaScript, Android and firmware targets; registers itself with every supported agent; Evidence IDs on every result",
         "One target per session; answers single-artefact questions, not corpus ones",
         "rea", "`rea doctor --json`, or `npx -y rea-agents@latest doctor --json`",
         "npx -y rea-agents@latest", _GH + "morluto/rea"),
    Tool("Ghidra", "core", "Analysis, decompilation, P-code, BSim, Version Tracking",
         "Transactions nest; one writer per program",
         _HEADLESS, "`$GHIDRA_INSTALL_DIR/support/analyzeHeadless` exists",
         "download a release and set GHIDRA_INSTALL_DIR", _GH + "NationalSecurityAgency/ghidra"),
    Tool("objdiff", "core", "Object-level byte comparison; the proof for Verified",
         "Compares objects, not behaviour",
         "cmd:objdiff-cli --version", "`objdiff-cli --version`",
         "cargo install objdiff-cli, or a release binary", _GH + "encounter/objdiff"),
    Tool("Toolchain of the target", "core",
         "The compiler the original shipped with (MSVC under Wine, old GCC, console SDKs)",
         "Must be identified by calibration, not guessed",
         "config:profile.compiler",
         "Project-specific; doctor reports the configured profile's compiler path",
         "project-specific; see the target's profile", None),
    Tool("uv", "core", "Runs this repo", "none",
         "cmd:uv --version", "`uv --version`",
         "curl -LsSf https://astral.sh/uv/install.sh | sh", _GH + "astral-sh/uv"),
    Tool("Node.js and npm", "core", "Runs REA", "REA needs Node 22.19+, 24.11+ or 26+",
         "cmd:node --version", "`node --version`",
         "https://nodejs.org or your package manager", None),

    Tool("Ghidra BSim", "matching",
         "Decompiler-feature similarity across a repository of programs",
         "Needs a database created and every program ingested first; empty results often mean that step never ran",
         _BSIM, "`$GHIDRA_INSTALL_DIR/support/bsim` exists",
         "ships with Ghidra; create a database before use", None),
    Tool("Ghidra Version Tracking", "matching",
         "Pairwise correlators (exact bytes, symbol names, function references) with Accepted and Rejected per match",
         "Two programs at a time",
         _HEADLESS, "`analyzeHeadless` exists (VT ships with Ghidra)",
         "ships with Ghidra", None),
    Tool("BinDiff", "matching", "Call-graph and flow-graph diffing between two binaries",
         "Pairwise; no corpus notion",
         "cmd:bindiff --version", "`bindiff --version`",
         "download a release from the project page", _GH + "google/bindiff"),
    Tool("VexIR2Vec", "matching", "Architecture-neutral function embeddings over VEX IR",
         "Embedding similarity is a hint, never identity",
         "python:vexir2vec", "Python import `vexir2vec`",
         "see url", _GH + "IITH-Compilers/VexIR2Vec"),

    Tool("BinKit 2.0", "calibration",
         "Ground truth: 371,928 binaries, 8 architectures, 23 compilers, 6 optimization levels. Says how matcher scores move with the compiler",
         "GNU packages only; no proprietary compilers",
         "config:binkit.dataset_dir", "Dataset directory configured",
         "download the dataset from the project page", _GH + "SoftSec-KAIST/BinKit"),
    Tool("FIN", "calibration",
         "Labels which calls in one debug-bearing ELF build were inlined in another, by comparing DWARF. Ground truth for how inlining hurts a matcher",
         "Needs IDA Pro (`--ida`), ELF, debug info in both builds. A dataset builder, not a matcher for stripped binaries",
         "config:fin.checkout", "checkout path and configured IDA path",
         "git clone the repo; IDA Pro is separate", _GH + "McGill-DMaS/FIN"),

    Tool("PANDA", "execution", "Whole-system record and replay, taint, introspection",
         "Models what QEMU models",
         "python:pandare", "Python import `pandare`",
         "see url", _GH + "panda-re/panda"),
    Tool("avatar²", "execution", "Orchestrates emulators and real hardware in one execution",
         "Hardware side does not scale",
         "python:avatar2", "Python import `avatar2`",
         "pip install avatar2", _GH + "avatartwo/avatar2"),
    Tool("Renode", "execution", "Embedded platform simulation with peripheral models",
         "Peripherals are functional, not physical",
         "cmd:renode --version", "`renode --version`",
         "download a release from the project page", _GH + "renode/renode"),
    Tool("Frida", "execution", "Dynamic instrumentation of live processes",
         "Observes; does not prove",
         "cmd:frida --version", "`frida --version`",
         "pip install frida-tools", _GH + "frida/frida"),
    Tool("Real-hardware traces", "execution",
         "Ground truth for timing and undocumented behaviour",
         "Manual; one device at a time",
         "config:hardware.trace_dir", "configured trace directory",
         "capture on the device and point the config at the directory", None),

    Tool("AFL++", "verification", "Differential fuzzing original vs recovered",
         "Finds differences; cannot prove absence",
         "cmd:afl-fuzz --version", "`afl-fuzz --version`",
         "apt install afl++", _GH + "AFLplusplus/AFLplusplus"),
    Tool("angr", "verification", "Symbolic execution over function pairs",
         "Path explosion; external effects unmodelled",
         "python:angr", "Python import `angr`",
         "pip install angr", _GH + "angr/angr"),
    Tool("Alive2", "verification", "Validates LLVM IR transformations under LLVM semantics",
         "IR only; LLVM semantics only",
         "cmd:alive-tv --version", "`alive-tv --version`",
         "build from source; see url", _GH + "AliveToolkit/alive2"),
    Tool("CounterTV", "verification",
         "Translation validation: unoptimized LLVM IR against the x86-32 the compiler produced from it, by counterexample-guided correlation",
         "x86-32 only; needs the source's IR; OOPSLA'20 Docker artefact with one commit (2020), 32 GiB RAM recommended",
         "cmd:docker image inspect oopsla20-ctv", "Docker image `oopsla20-ctv` present, or checkout path",
         "load the OOPSLA'20 Docker artefact; see url", _GH + "compilerai/counter"),
    Tool("VeriBin", "verification", "Binary-level patch safety via symbolic execution (NDSS'25)",
         "Patch-shaped changes, not whole-program equivalence",
         "config:veribin.checkout", "checkout path",
         "git clone the repo", _GH + "purseclab/VeriBin"),

    Tool("ReAgent", "recovery",
         "Reverser/checker model loop over Ghidra context that emits C/C++ candidates, with build, test and structural gates and a GREEN/YELLOW/RED parity verdict",
         "Its own gates are conservative verification, not byte parity; candidates still go through objdiff here",
         "reagent", "`re-agent doctor`",
         "see url", _GH + "Dryxio/reagent"),
    Tool("rev.ng", "recovery", "Lifting to LLVM IR and decompilation",
         "Alternative lifter; outputs are Advisory",
         "cmd:revng --version", "`revng --version`",
         "see url", _GH + "revng/revng"),

    Tool("SQLite (stdlib)", "evidence", "Identity graph and findings store shipped with this repo",
         "Single writer; no branch merges",
         "python:sqlite3", "always present",
         "ships with Python", None),
    Tool("Temporal", "evidence",
         "Durable campaigns, retries, execution history; the job queue shared compute would use",
         "Activities can run twice; writes must be idempotent",
         "cmd:temporal --version", "`temporal --version`",
         "brew install temporal, or a release binary", _GH + "temporalio/temporal"),
    Tool("DVC", "evidence", "Content-addressed artefact storage and pipelines",
         "Storage, not meaning",
         "cmd:dvc version", "`dvc version`",
         "pip install dvc", _GH + "iterative/dvc"),
    Tool("OpenLineage", "evidence", "Job/input/output lineage records",
         "Describes runs; does not judge findings",
         "python:openlineage", "Python import `openlineage`",
         "pip install openlineage-python", _GH + "OpenLineage/OpenLineage"),
    Tool("in-toto", "evidence", "Attestations of who ran what on which inputs",
         "Attests process, not correctness",
         "cmd:in-toto-run --version", "`in-toto-run --version`",
         "pip install in-toto", _GH + "in-toto/in-toto"),
    Tool("cosign", "evidence", "Signs receipts and attestations",
         "A signed wrong answer is still wrong",
         "cmd:cosign version", "`cosign version`",
         "go install github.com/sigstore/cosign/v2/cmd/cosign@latest, or a release binary",
         _GH + "sigstore/cosign"),
    Tool("Dolt", "evidence",
         "Versioned SQL with branches and row-level merge conflicts, if per-agent branching is measured to be needed",
         "Records conflicts; does not resolve them; runs a server",
         "cmd:dolt version", "`dolt version`",
         "brew install dolt, or a release binary", _GH + "dolthub/dolt"),

    Tool("Ghidra Server", "concurrency",
         "Shared repository with checkout and checkin per program",
         "RMI over SSL; checkout is per file, not per function",
         "config:ghidra_server.address", "configured host:port reachable",
         "ships with Ghidra (server/ directory)", None),

    Tool("ghidra-rpc", "bench",
         "A persistent PyGhidra daemon per `.gpr` with a JSON CLI; autosaves after every command; can write raw bytes",
         "One program state per daemon. Never start it against a project another writer has open",
         None, "bench", "see url", _GH + "cellebrite-labs/ghidra-rpc"),
    Tool("RenderDoc", "bench", "Graphics engines: frame, shader, resource, draw-call capture",
         "No D3D9/D3D10 or legacy OpenGL compatibility profile",
         None, "bench", "download a release from the project page", _GH + "baldurk/renderdoc"),
    Tool("apitrace", "bench", "Older graphics APIs RenderDoc skips", "Tracing, not analysis",
         None, "bench", "apt install apitrace", _GH + "apitrace/apitrace"),
    Tool("STOKE", "bench", "x86-64 instruction-level equivalence and synthesis, as a reference",
         "Research prototype, no active development, per its maintainers",
         None, "bench", "build from source; see url", _GH + "StanfordPL/stoke"),
    Tool("SBridge", "bench",
         "Source-to-binary function similarity by control-block matching; 75.13% recall@1 on 3,904 BinKit binaries with about 40% inlined functions (FSE'26)",
         "No public artefact located",
         None, "bench", "see url", "https://dl.acm.org/doi/10.1145/3797090"),
    Tool("O2NMatcher", "bench", "Source function sets for binary-to-source matching under inlining",
         "Research code",
         None, "bench", "see url",
         _GH + "island255/binary2source-matching-under-function-inlining"),
    Tool("vSim", "bench", "Semantic-value similarity, for benchmark comparison",
         "Adopt only if it beats current matchers on an independent corpus",
         None, "bench", "see url",
         "https://www.ndss-symposium.org/ndss-paper/vsim-semantics-aware-value-extraction-for-efficient-binary-code-similarity-analysis/"),
    Tool("Co2FuLL", "bench", "LLM-verified binary similarity, for benchmark comparison",
         "Same bar as vSim",
         None, "bench", "see url", None),
)


def select(layer: str | None) -> tuple[Tool, ...]:
    return TOOLS if layer is None else tuple(t for t in TOOLS if t.layer == layer)


def _add_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--layer", choices=LAYERS, help="show one layer only")
    p.add_argument("--markdown", action="store_true", help="print the stack table")


def _run(args: argparse.Namespace) -> int:
    tools = select(args.layer)
    if args.markdown:
        print("| Tool | Job | Limit | Doctor check |")
        print("|---|---|---|---|")
        for t in tools:
            cell = f"[{t.name}]({t.url})" if t.url else t.name
            print(f"| {cell} | {t.job} | {t.limit} | {t.doctor_text} |")
    else:
        for t in tools:
            print(f"{t.name:<18} {t.layer:<13} {t.detect or 'bench'}")
    return 0


register("tools", _add_parser, _run, "list the stack and how each tool is detected")
