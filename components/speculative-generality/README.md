# Speculative Generality

**Deliberately implement hypothetical future capability. Reject YAGNI as the default
for this workflow. Require working behavior and honest verification.**

A focused Claude Code plugin: three manually invoked skills, three read-only
advisory agents, and one writing coordinator (the main session). The role-based
protocol draws on 2023–2024 research; the packaging follows current host docs.
The original source retains its historical investigation. This distribution's scope is described in the [integration guide](INTEGRATION.md).

Version **0.1.0**. Research-informed, not empirically validated for architectural
quality. Package checks and behavioral validation are different; see
the [integration guide](INTEGRATION.md) for this source bundle's verification boundaries.

## Use it

Extract `speculative-generality-0.1.0.zip`. From your target project's directory:

```sh
claude plugin validate /absolute/path/to/speculative-generality
claude --plugin-dir /absolute/path/to/speculative-generality
```

The path is the extracted directory containing `.claude-plugin/plugin.json`, not
its `.claude-plugin` subdirectory. Use a current Claude Code version that supports
the documented plugin/skill/subagent fields. No AutoGen or MetaGPT installation,
Python environment, separate API keys, marketplace, or MCP server is required by
the plugin itself. Your host's normal authentication, model usage and costs apply.
The package is loaded for that session; it does not install itself globally. [H1]

```text
/speculative-generality:plan Examine the storage subsystem. Anticipate substantially
 different backends, independent API consumers, and future schema changes.

/speculative-generality:build Implement the agreed storage capability plan. Preserve
 current defaults and existing callers. Do not provision external services.

/speculative-generality:review Review src/storage and its tests against that plan.
```

Enter each example as one prompt. BUILD can also start directly from a task and
perform its own planning. PLAN does not silently start BUILD.

| Skill | Result | Workspace effects |
| --- | --- | --- |
| `plan` | Hypothetical scenarios, capability contracts, implementation/test plan | No execution or intentional edits |
| `build` | Working code, tests, capability ledger, actual evidence | Coordinator may edit and execute within authorization |
| `review` | Contract counterexamples, missing future capability, evidence gaps | No execution or intentional edits |

## What is different from YAGNI

A missing second implementation or current caller is not sufficient grounds to
remove or refuse an abstraction. Nor is an unconfirmed future demand. The default
is to build coherent speculative support now, including ambitious futures that
fit the task. The workflow does not impose a "likely to be needed soon" gate.

The challenge is instead: **What future behavior does this promise, can a consumer
actually use it, and what would demonstrate that it works?** An inert setting,
empty plugin registry, stub adapter, or future-work paragraph does not satisfy it.

One real backend plus an implemented seam and an independent consumer test may
verify extensibility. That does not establish an unimplemented cloud integration.
Future demand may be hypothetical; implementation and test claims must not be.

Explicit narrow user instructions, security constraints, compatibility obligations,
and external-spending permissions still apply. This policy is not permission to
change the whole product after the user requested a confined fix.

## Collaboration

The main session dispatches actual separate agent contexts and relays their
structured proposals. This is coordinator-mediated conversation, not a direct
peer-to-peer messaging service.

| Role | Contribution | Does not do |
| --- | --- | --- |
| `future-scout` | Invents concrete future scenarios and challenges present assumptions | Design the whole architecture or write code |
| `extension-architect` | Independently identifies change barriers, then answers scenarios with contracts and implementation paths | Dismiss speculation because demand is unconfirmed |
| `contract-challenger` | Supplies counterexamples and checks code/evidence against promised capability | Run a YAGNI deletion pass or claim unrun tests passed |
| Main session | Controls scope, relays proposals, implements, runs checks, reports evidence | Treat agent consensus as proof |

Initial scout and architect inputs exclude each other's proposals. The architect
then receives the scout's scenarios; the challenger critiques the combined
contracts; at most one design revision follows. After implementation the challenger
reviews real source and execution records. One repair/recheck cycle is allowed.

No more than five advisory calls for PLAN, seven for BUILD, and one for REVIEW.
Those total-call/repair limits are instructions, not a hard cost meter. Each agent
also declares the host-supported `maxTurns: 12` and read-only `Read, Grep, Glob`
tools. The default `model: inherit` uses the session model; different roles do not
mean different model families. [H2]

## Safety and boundaries

Skills are manual-only. PLAN/REVIEW additionally deny common shell/write tools for
the invoking turn. Those denials are not a universal sandbox or a denylist of every
possible connected tool; instructions prohibit other write routes too. Host
permissions remain the security boundary. Do not use permission-bypass mode to
"fix" a blocked workflow. Tool-denial lifecycle is host-dependent. [H3]

There are no execution hooks, background loops, spawned services, hidden state,
telemetry, automatic dependency installation, or global policy edits. A copied
project-rule fragment is optional; nothing installs it automatically.

Do not enable conflicting automatic YAGNI-enforcement hooks for the same task
without deciding the precedence yourself. The plugin will report a material policy
conflict rather than rewriting another plugin's rules.

If native subagents are unavailable, the workflow reports that limitation. A
single-context fallback requires your agreement and is explicitly labeled; it is
not presented as independent collaboration.

## Package contents

```text
.claude-plugin/plugin.json      Native plugin manifest
skills/{plan,build,review}/     Three entry-point skills
agents/                        Three original role prompts
rules/                         Policy, conversation protocol, verification contract
templates/                     Handoff envelope and scenario/capability work record
research/                      Primary-source investigation and source-access audit
evals/                         Twelve behavioral cases and matched-budget evaluation plan
scripts/validate.py             Offline package checks, Python 3.9+
tests/                         Validator regression tests
PORTABILITY.md                 Honest host/porting boundaries and optional rule fragment
VALIDATION.md                  Actual validation record
```

## Local package checks

Python is only needed for maintenance checks, not to run the prompt plugin:

```sh
cd /absolute/path/to/speculative-generality
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

The validator intentionally accepts only this package's JSON-valued YAML frontmatter
subset. It is not a general YAML parser and does not replace `claude plugin validate`.
It checks package shape and references, not whether a model follows the prompts.

Consult the original source's evaluation plan before making any claim that collaboration
outperforms a single well-prompted agent. The role count, round budget and scenario
batch sizes are editable design choices, not research-established optima.

## Host references

[H1] [Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference), accessed 2026-09-22.

[H2] [Claude Code subagent reference](https://code.claude.com/docs/en/sub-agents), accessed 2026-09-22.

[H3] [Claude Code skills reference](https://code.claude.com/docs/en/skills), accessed 2026-09-22.
