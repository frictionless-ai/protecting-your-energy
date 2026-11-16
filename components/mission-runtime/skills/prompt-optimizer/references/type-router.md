# Prompt type router

Classify the target before writing. One mega-template produces
ceremony the job does not need.

## Contents

- [Routing table](#routing-table)
- [Instruction layers](#instruction-layers)
- [Length](#length)
- [Intervention](#intervention)
- [Kind-specific standing rules](#kind-specific-standing-rules)

## Routing table

| Target | What to fix | What to leave free |
|---|---|---|
| Execution spec (default) | The compile-spec slots | The executor's route |
| System or developer prompt | Durable cross-task behavior, hierarchy, eval plan | Current-task facts, guessed project structure |
| Coding or repository agent prompt | Outcome, discovery path, evidence of done | Implementation route, stack guesses |
| Repo instruction file | Standing conventions, closest-file-wins | One-off task steps |
| Code review prompt | Issue intent, evidence, risk, verdict shape | Implementation |
| General task prompt | Goal, audience, constraints, output, check | Process theater |
| Research prompt | Question, source bounds, recency, conflict policy | A canned search sequence |
| Extraction or classification | Schema, labels, nulls, edge cases | Personality |
| Image or video prompt | Scene or edit, references, preservation, exact text | Coding-agent contracts |
| Prompt audit | Type row above + the quality checklist | New scope |

A template is a menu. Omit sections that do not earn their place. Do
not fill an empty slot with plausible detail.

## Instruction layers

Map the runtime before writing a durable prompt.

| Layer | Put here | Keep out |
|---|---|---|
| System / developer | Durable role, scope, authority, stable tool policy | One task's data, guessed file map |
| User / task | Current objective, supplied context, this deliverable | Global policy that must survive every request |
| Project instruction file | Verified commands, conventions, recurring gotchas | Generic language rules, stale guesses |
| Tool description | Capability, inputs, outputs, side effects | Personality, duplicate global rules |
| Deterministic control | Permissions, schemas, hooks, validators | Advisory prose that must never fail |

When a requirement can be enforced outside the prompt, put it there.
A prompt is technical debt: every rule must earn its place against a
baseline with no custom prompt.

## Length

- Tiny one-off: a few lines.
- Normal task: objective, context, constraints, output, check.
- Complex or risky: add process, tool policy, uncertainty, verification.
- Durable system prompt: stable behavior only, then eval and ablate.

A larger prompt is justified by task hardness, a strict output
contract, real risk, or a measured miss — not by a desire to look
complete.

## Intervention

Match the rewrite to the draft:

| Level | When | What to do |
|---|---|---|
| none | Already clear, or text/code to act on as-is | Return it near-unchanged |
| light | Clear but messy | Tidy structure; add no scope |
| normal | Vague but answerable | State assumptions; keep moving |
| strong | Missing a fact that would make the answer wrong or unsafe | Question packet; still sketch the shape |

Prefer delivering over interrogating.

## Kind-specific standing rules

**System / developer.** Start from the platform default. Add a rule
only for a real product requirement, an authorization boundary, a
measured recurring miss, a tool contract the runtime does not
enforce, a shared output contract, or a material safety risk. Durable
behavior stays here; current-task facts do not.

**Coding / repo agent.** Apply the evidence ceiling. At C0 the prompt
is discovery-first. Detect stack from repo evidence. Smallest
semantically complete change; preserve behavior unless changing it is
the ask. Live verification over asking the user to test what the
agent can test. Subagents only when the work is large, parallel, or
review-heavy; one primary owner.

**Code review.** Restate issue intent. Inspect the diff and the
surrounding code. Root cause vs symptom. Minimality. Behavior drift.
Data contracts. Runtime, UI, security, and performance risk. Tests
that would fail for the right bug. No approval without evidence.
Separate blockers from nits.

**Research.** One precise question plus the decision the answer should
support. Source types, domains, geography, and a date window.
Conflicts and sparse results are first-class: say what was not found.

**Extraction.** Schema, required vs optional, null policy, one
ambiguous example. Extra keys forbidden when the consumer is a
parser.

**Image / video.** Describe a coherent visual result. Classify
generate vs edit vs preserve vs combine vs text-layout vs diagram vs
motion. Supplied references have roles. Edits name change vs
preserve. Quote exact visible text. Tool parameters stay outside
visual prose when a structured argument exists. Do not inject a
coding-agent contract into a picture prompt.
