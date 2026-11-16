---
name: prompt-optimizer
description: >
  Manually rewrite a prompt for a named downstream model, inspect why
  a prompt is weak, or author a reusable prompt as the artifact.
  Invoke as /prompt-optimizer [target-model] followed by the prompt
  text. The first token is a target model when it matches the plugin
  model index; otherwise the whole argument is the prompt.
  Use when the user wants to see the engineered prompt, compare
  targets, debug a rewrite, "write a system prompt", "audit this
  prompt", "make this prompt better", "code review prompt",
  "image prompt", or "prompt eval" without running the automatic
  runtime.
disable-model-invocation: true
argument-hint: "[target-model] <prompt>"
arguments:
  - target
  - prompt
metadata:
  version: "0.6.0"
---

# Prompt optimizer

This is the manual path. The user asked to see, debug, author, or
audit a prompt. It is not the automatic runtime, and it is not the
host field that selects which model executes this skill.

`$target` is the optional first token. `$prompt` is the rest. If the
skill was invoked with a single blob in `$ARGUMENTS`, parse it as
follows.

## Parse the target

1. Read `${CLAUDE_PLUGIN_ROOT}/references/models/index.md`.
2. Take the first whitespace-separated token of `$ARGUMENTS`.
3. Normalize and match the index table.
4. On a match: that token is the target; the remainder is the user's
   prompt. Load the family file the table names, plus
   `${CLAUDE_PLUGIN_ROOT}/references/models/generic.md`.
5. On no match, or an empty argument, or `generic` / `auto` /
   `default`: use only the generic file. If the first token did not
   match, do **not** strip it — the entire argument string is the
   prompt. Say that the target was unknown and that the generic core
   was used.
6. If the remainder is empty after a matched target, ask for the
   prompt (one line) and stop.

## Classify

Read `references/type-router.md` before writing. The default artifact
is an execution spec. A system prompt, review rubric, image prompt,
or eval request is a different row. Do not force the compile-spec
template onto a picture prompt or a durable system prompt.

Specificity follows
`${CLAUDE_PLUGIN_ROOT}/skills/prompt-runtime/references/evidence-calibration.md`.

## Compile

For an execution spec, follow the automatic runtime's compile
procedure — read
`${CLAUDE_PLUGIN_ROOT}/skills/prompt-runtime/references/compile-spec.md`
and, when the prompt is a fragment, the intake reference beside it. Apply the family overlay only as calibration on top of the
generic core: effort knobs, verification policy, output-contract
mechanics, context order. Do not copy a provider manual into the
result.

Preserve intent and language. Do not invent requirements. Do not
lengthen a prompt that is already excellent — return it near-unchanged
and say so.

Decompose a vague ask into concrete issues. Separate investigation
from action. Infer what done looks like from context, and convert
implicit assumptions into tagged requirements. For a bug, name the
diagnostic questions; for a feature, name constraints and edges; for
a review, name the criteria. Keep the user's terminology and examples.
Do not expand or shrink scope unless they asked.

Conversation context that the current message depends on is recovered
the same way as the automatic path. Presentation preferences are
listed separately and are not mixed into the execution spec.

## Check

Read `references/quality-checklist.md` before returning. Read
`references/eval-iteration.md` when the user asked for eval cases, an
ablation, or a measured comparison. Run
`python3 scripts/make_prompt_eval.py` to write a new manifest; it
refuses to overwrite.

## Output

Return, in this order:

1. The artifact — an execution spec, or the authored / audited prompt
   the type-router row called for.
2. Response-style notes held back from an execution spec, if any.
3. A short delta: what was added, dropped, inferred; which family
   file applied (or generic fallback); type row and evidence ceiling.
4. An offer to execute an execution spec now via the automatic
   runtime's chassis map. Do not execute unless the user accepts.
   Do not execute an authored system prompt or review rubric.

If the original prompt was already complete, step 1 may equal the
original plus at most a recovered-context line, and step 3 says
"minimal intervention."
