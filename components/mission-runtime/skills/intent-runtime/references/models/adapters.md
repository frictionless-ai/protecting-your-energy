# Adapters

Load only when the caller named `target_model`. Unknown snapshot → portable base. Do not guess a family.

```
compiled_prompt
execution_hints:
  target_model
  effort
  verbosity
  structured_output_schema
  tool_policy
  context_policy
```

Put knobs in `execution_hints`, not in the prose.

## claude-fable-5

- Effort: `low` | `medium` | `high` | `xhigh`. Default `high`. Thinking is adaptive.
- One short instruction per behavior.
- Keep user-given reasons (I2).
- Act when you have enough. Do not re-derive settled facts.
- Pause only for destructive work, scope change, or user-only input.
- Long runs: audit each claim against a tool result from this session.
- Do not tell the model to echo its reasoning.
- Retention: 30-day; not ZDR.

## claude-opus-5

- State scope. Do not add extra verify/double-check instructions.
- Set written-deliverable length.

## claude-sonnet-5

- State scope for every section.
- Specify the full turn. Use structured output when format is load-bearing.

## gpt-5.6-sol / gpt-5.6-terra / gpt-5.6-luna

- `reasoning.effort` none→max; `reasoning.mode: pro`; `text.verbosity` low|medium|high.
- State each instruction once. Use `text.verbosity` instead of "be concise".
- State autonomy once.

## gemini-3.x

- Short instructions. Core request and negations last.
- Artifacts first, then "Based on the preceding information…".

## deepseek-v4

- Instruction first, delimited context. Enable thinking for multi-step work.

## portable-base

Order: Objective, Why, Recovered context, Constraints, Scope, Non-goals, Evidence, Output, Assumptions, Chassis. No vendor knobs.
