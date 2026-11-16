# Prompt-runtime architecture

Plugin version 0.6.0. This is the selected design for automatic
prompt engineering on Claude Code Agent Skills.

## Selected runtime design

Two prompt skills, one shared model-guidance tree, the existing
ten-agent chassis pool, and an eval harness.

- `skills/prompt-runtime/` runs **inline** in the parent conversation.
  It compiles a self-contained execution spec, delegates via the Task
  tool, and renders the result.   Intake is one reference: recover at full fidelity, auto-answer
  settled branches, then interview remaining ones (thoroughness
  follows size). Compile owns intervention, diagnostic depth, approach
  scale (score before dispatch; probe vs ruler), and the C0/C1/C2
  evidence ceiling.
- `skills/prompt-optimizer/` is manual
  (`disable-model-invocation: true`) and takes an optional
  `[target-model] <prompt>` argument. The same skill authors or audits
  a reusable prompt (system, review, image, eval) when that is the
  artifact.
- `references/models/` is data: family overlays loaded by the
  optimizer. Instruction surfaces stay model-agnostic. Family files
  cover the routed slugs in the index, including Kimi, GLM, Nova, Phi,
  Jamba, Perplexity, and MiniMax in `others.md`.
- `agents/` is unchanged. Chassis are sound; mission ceremony is what
  left the automatic path.

A single mega-skill cannot separate the always-loaded automatic surface
from the argument-driven manual surface. A dozen auto-invocable
micro-skills would compete in the same 1,536-character listing
economy. Hooks were
rejected as the primary router — the product must use the supported
discovery mechanism. A `UserPromptSubmit` hint remains a documented
fallback if measured recall is insufficient. The 12-case smoke
eval (structured Skill-tool detection) measured recall 0.25 and
precision 1.0: fragments the host can answer itself under-fire;
adversarial and meta cases do not false-trigger.

## How semantic activation works

Claude Code lists `description` + `when_to_use` (truncated at 1,536
characters) and the model chooses whether to invoke the skill. There is
no configurable embedding threshold. Trigger quality is those two
fields, written from corpus families (fragments, deixis, frustration,
vague lookup, mixed style+task) and evaluated independently of answer
quality. `mission` and `mission-brief` are manual-only so they do not
steal that surface.

## How prompt reconstruction works

The current message is treated as a delta. The compiler recovers the
real objective, selected earlier-turn facts, semantic constraints,
scope, evidence, and tagged assumptions. It adds the minimum structure
that makes execution reliable. It does not invent requirements, broaden
scope, or rewrite uncertainty as certainty. An already-complete prompt
gets minimal or no rewrite.

## How task vs presentation is separated

A clause enters the executor spec if removing it could change what work
is done or what answer is correct. It stays at the parent if it only
changes how the finished result reads. Quantities, time ranges,
environment, and source requirements survive. Tone, length, formatting,
and persona stay behind. Ambiguous cases default to the spec. The
rubric is a functional test, not a phrase list.

## How delegation works

The spec is the Task prompt. The executor is a capable specialist from
the existing roster (research-analyst, regression-investigator,
implementation-engineer, …). Score complexity, urgency, locality,
taste, and volume before picking a shape. A probe checks that a
mechanism fires; a ruler checks that the work meets the bar. The route
is left free. No chain-of-thought requests, no ritual scaffolding. An
independent non-authoring check is a dispatch decision for
consequential changes, not always-on prose — current model families
disagree on verification scaffolding, and that disagreement is recorded
in `references/models/anthropic.md`.

## How context is transferred

`context: fork` is not used for the compiler: a fork has no
conversation history, and recovery *is* the product. Selected facts
cross the boundary inside the spec. Disk-resident material travels as a
path plus “read before acting.” Whole transcripts are not dumped.

## How model-specific prompting is handled

The automatic path uses the model-agnostic core in
`references/models/generic.md`. The manual optimizer routes the first
argument through `references/models/index.md` to a family file, or
falls back to generic and says so. Unknown names are not stripped from
the prompt. Effort/thinking remain host knobs.

## Why this over the alternatives

- Keep the old mission-first UX: users would still have to declare a
  mission. Rejected.
- Compile inside `context: fork`: loses the conversation. Rejected.
- One enormous SKILL.md: blows the body budget and mixes automatic
  with manual. Rejected.
- CrewAI-style role/goal/backstory: 2023-era; not the 2026 bar
  (Agent Skills + AGENTS.md + destination-over-route). Rejected.
