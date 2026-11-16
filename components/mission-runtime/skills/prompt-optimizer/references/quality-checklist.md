# Prompt quality checklist

Run before returning a generated or audited prompt.

## Contents

- [Must pass](#must-pass)
- [By kind](#by-kind)
- [Prompt debt](#prompt-debt)

## Must pass

- The goal is specific and the done state is testable.
- Context is relevant, not a dump.
- Source or user data is separated from instructions.
- Constraints are concrete and enforceable.
- Output format is explicit when a consumer will parse it.
- Examples appear only when they improve consistency.
- Verification exists when the outcome matters.
- Failure and uncertainty behavior is defined for factual, risky, or
  incomplete tasks.
- Destructive actions are gated.
- Unsupported assumptions are not presented as facts.
- Missing project facts are marked unknown and assigned to inspection.
- Type and evidence ceiling (C0 / C1 / C2) were classified first.
- Specificity does not exceed evidence.
- The prompt is no larger than the task and the eval evidence justify.
- The user's language and identifiers are preserved.

## By kind

**System or developer.** Starts from a platform-default or
no-custom-prompt baseline. Holds durable cross-task behavior, not
current-task data. Separates advisory rules from deterministic
controls. States each instruction once and resolves hierarchy
conflicts. Has baseline, minimal, and candidate variants for
important cases. Accepts a shorter or blank custom prompt when it
performs better.

**Coding-agent.** C0 stays discovery-first. C1 labels implementation
theories as hypotheses. C2 uses project specifics only when verified.
Stack and tooling are discovered from repo evidence. Subagents appear
only when they create leverage. Live verification is preferred. Done
is explicit. The final report is terse unless a rigid structure is
required.

**Code review.** Issue intent, diff evidence, root-cause test,
minimality, risk, verification, verdict. An approval names the
evidence it rests on.

**Image or video.** Coherent visual result. References have roles.
Edits distinguish change from preservation. Exact visible text is
quoted. Negative constraints target likely failures, not a giant
ban-list.

**Research.** Question, source bounds, recency, conflict and
insufficient-evidence policy, ranked findings.

## Prompt debt

Delete or rewrite a rule that is generic steering with no measurable
purpose, that was added for an old executor and no longer helps, that
conflicts with another rule, or that duplicates a tool, schema, or
permission already in force.
