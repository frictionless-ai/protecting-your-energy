---
name: intent-runtime
last_updated: 2026-09-01
---

# Intent compiler

A user expresses intent as naturally as they can — incomplete, lazy,
poorly phrased, or technically unsophisticated. This plugin compiles
that into high-quality execution. The user should only need to know
what they want, not how an expert would ask for it.

They do not specify professional process, terminology, tools,
validation, research standards, debugging procedure, testing
expectations, or implementation detail. Those are means. The compiler
supplies them.

Field notes: `docs/research/intent-compiler.md` (Firecrawl, 2026-09-01).
Industry default is the same: DSPy / Artic-style compile, not "teach
the user to prompt."

## Approach

Classify → distill a solution spec to intent (`distill-intent`) →
infer omitted context → compile an ExecutionContract → fan out
chassis specialists from that intent. Each specialist supplies how
for its slice. After a miss, distill STRATEGY, field notes, and the
observation back to intent, then recompile — a process repair is not
the new goal. Scope grows only when tagged `[entailed]`.

## Not this plugin

- Teaching users to write better prompts, or showing them the
  engineered prompt
- Elicitation cards / brief quizzes
- Separate status, resume, telemetry, or live-eval products
- Telemetry that leaves the machine
