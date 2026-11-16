# Adapter registry (capability-based, snapshot-keyed)

Load this file only when the caller passed an explicit `target_model`.
If none was passed, do not read this file, do not infer a snapshot, and
do not describe model differences.

Rendering produces two halves so provider knobs stay out of the prose:

```
compiled_prompt          # role-separated: durable policy in the system/developer
                         # slot (only if the calling app owns that slot),
                         # artifacts in delimited blocks, task statement last
execution_hints:
  target_model           # exact snapshot
  effort                 # provider-native effort / thinking level
  verbosity              # provider-native verbosity control where it exists
  structured_output_schema   # when response_contract specifies machine shape
  tool_policy            # tools allowed/required
  context_policy         # reasoning persistence / context handling flags
```

An explicit but unknown snapshot → use the portable base and note the
registry gap. Do not substitute a guessed family. When a listed snapshot
changes, re-run that adapter's eval cases before trusting old rendering
rules.

## Registry

### claude-fable-5
- Capabilities: adaptive thinking; effort levels; strong instruction
  following; subagent orchestration.
- Prompt style: brief. Over-prescriptive scaffolding degrades output — one
  short instruction per behavior. Preserve user-given reasons; never
  manufacture them (I2). For agentic work include an autonomy boundary and,
  for long runs, progress-grounding ("audit each claim against a tool result
  from this session"). Never instruct the model to echo or explain its
  internal reasoning (triggers the reasoning-extraction refusal).
- Retention note: 30-day provider retention; excluded from ZDR.

### claude-opus-5
- Capabilities: 1M context; strong self-verification; effort levels.
- Prompt style: add an explicit scope constraint (the model self-expands
  scope); do NOT add verification or double-check instructions (it
  self-verifies; instructions compound). Calibrate written-deliverable
  length explicitly.

### claude-sonnet-5
- Capabilities: adaptive thinking default-on; effort levels; structured
  outputs; no sampling params.
- Prompt style: literal instruction following — state scope explicitly
  ("apply to every section, not just the first"). Complete single-turn
  specification beats progressive clarification. Use structured outputs for
  format-critical work.

### gpt-5.6 family (sol / terra / luna)
- Capabilities: `reasoning.effort` none→max; `reasoning.mode: "pro"`;
  persisted reasoning via `reasoning.context`; `text.verbosity`
  low/medium/high; JSON-schema structured output; programmatic tool calling.
- Prompt style: lean — state each instruction once; current guidance shows
  measurable gains from removing repeated instructions. Use
  `text.verbosity` instead of prose brevity demands. State the
  autonomy/approval policy once, compactly (repeating "ask first" causes
  unnecessary approval requests). Map contract complexity to
  `reasoning.effort`; reserve pro mode for quality-critical work.

### gemini-3.x
- Capabilities: `thinking_level`; system_instruction; long context.
- Prompt style: concise, direct instructions (verbose prompts cause
  over-analysis). Place the core request and negative constraints at the
  END of the prompt. Artifacts above, question after, anchored with
  "Based on the preceding information…". Leave temperature at default.

### deepseek-v4 (flash / pro)
- Capabilities: OpenAI/Anthropic-compatible chat surface; system role;
  thinking + reasoning-effort flags.
- Prompt style: GPT-style structure (instruction-first, delimited context);
  enable thinking for multi-step tasks.

### portable-base
- No vendor knobs. Delimited sections in this order: context block, artifact
  blocks, task statement, task constraints, done-conditions, output format.
- Used for unknown targets and for the inline fast path (trivial contracts
  rendered by the primary agent without the prompt-engineer subagent).
