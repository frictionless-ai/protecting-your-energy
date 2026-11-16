# Other provider families

Fetched 2026-08-13. Apply the matching section on top of
[generic.md](generic.md). Llama is vintage-flagged (2025-04); no 2026
first-party prompting page was found.

## Mistral

Sources: docs.mistral.ai prompting + reasoning + native-reasoning
deprecation.

- One line: “You are X, your task is Y.” Purpose, not a persona novel.
- Hierarchical Markdown. The prompt must be executable with no outside
  context.
- Decision trees instead of contradictory bullets.
- Worded scales, not numeric 1–5. Do not ask the model to count words.
- JSON via structured outputs, not prompt-only.
- `reasoning_effort="high"` for agentic/code. Replay the full assistant
  message including think chunks.
- Do not target `magistral-*` (deprecated). Do not wrap chain-of-thought
  in `<think>` strings.

## DeepSeek

Sources: api-docs.deepseek.com (V4-Flash-0731, V4-Pro-0813), thinking
mode, JSON mode.

- Do not chain-of-thought-prompt. Set `thinking` + `reasoning_effort`
  (`low` / `high` / `max`). `medium` / `xhigh` map to `high`.
- Pass `reasoning_content` back on tool loops or the API returns 400.
- JSON: `response_format=json_object` **and** the word “json” plus an
  example in the prompt.
- Keep the system line short unless retrieval or a real constraint
  needs more.
- Sampling parameters are no-ops in thinking mode.

## xAI / Grok

Sources: docs.x.ai Grok 4.6, reasoning, prompt-caching.

- Reasoning cannot be disabled. Effort is `low` / `medium` / `high`
  (default) / `xhigh` (4.6+).
- Front-load the static prefix (system, few-shot, docs). Append-only
  history. Return reasoning content when `store:false` or cache misses.
- Do not send `presencePenalty` / `frequencyPenalty` / `stop`.
- `grok-4.20-multi-agent`: effort is **agent count**, not thinking
  depth. Special-case that slug.
- Foundry community copy that says “encourage step-by-step” is weaker
  than the first-party reasoning page. Do not encode it.

## Meta / Llama (2025-04 vintage)

Source: developer.meta.com Llama 4 prompt formats. No 2026 PE page
found.

- If talking to a raw Llama 4 tokenizer, emit the official header/eot
  tokens. Hosted chat APIs usually wrap this.
- Do not paste Meta's long conversationalist system prompt into a
  coding commission. Optional short system to cut refusals.
- Knowledge cutoff August 2024 if the task is time-sensitive.
- Re-check developer.meta.com at the next refresh; this section is
  flagged stale-risk.

## Cohere

Sources: building-a-chatbot-with-cohere (examples use
`command-a-plus-05-2026`), Command A plus model card.

- System always outranks user.
- System headers in this order: `## Task and Context` then
  `## Style Guide`.
- Prefer the `documents` RAG slot plus short instructions over a
  stuffed monolith.
- Pass full `messages` history.

## Qwen

Sources: qwen.readthedocs.io concepts + quickstart; Alibaba Model
Studio function-calling (lists 3.5–3.8).

- No default system message. Add a system block only for real
  constraints.
- Thinking on/off is `enable_thinking` or `/think` `/no_think` (last
  instruction wins), not “think step by step.”
- Keep thinking blocks only on the last round except multi-step tool
  use.
- Prefer the `tools` parameter over a hand-written Hermes system block.
- Sampling is host config: thinking 0.6 / 0.95; instruct 0.7 / 0.8 +
  presence_penalty 1.5. Do not write those numbers into the prompt.

## Kimi / Moonshot

Sources: platform.kimi.ai prompt best practices.

- Preserve the user's language. Do not translate a Chinese ask into
  English prompt jargon.
- One role, one task, explicit source limits and output length.
- Delimit reference material. Say whether the answer may use only that
  material.
- For long context, name what to extract, skip, preserve, and how to
  handle missing evidence.
- One compact example for a strict format. Tool intent is an outcome,
  not a pretend capability.

## GLM

Sources: docs.z.ai thinking mode, function calling, structured output,
context caching.

- Name the surface: chat, coding, tool use, extraction, or multimodal.
- Thinking is a host control, not a "think step by step" sentence.
- Long-horizon work needs a goal, done criteria, state to keep, allowed
  files or tools, and a stop rule.
- Structured extraction uses a field contract and a missing-value
  policy. Stable context goes in the cacheable prefix.

## Nova

Sources: docs.aws.amazon.com Nova prompting guide.

- Name the task type first (analysis / generation / extraction).
- Bind each modality to a job: what to take from the image or video,
  and how it combines with the text.
- Decompose as Objective → Input → Process → Output.
- Enterprise constraints are a list the answer must flag against.

## Phi

Sources: Phi Cookbook; Azure prompting techniques.

- Keep the prompt short. The window is small.
- Narrow the job. Pin patterns with one input → output example.
- Code shape: language, task, input example, output example,
  constraints. Return only what was asked.
- Do not assume large-model world knowledge.

## Jamba

Sources: docs.ai21.com prompting guide.

- Instruction first, then data, then a short hint that restates the
  requested output.
- Prefer stated target behavior over a long prohibition list.
- Label where each source starts and ends. Allow "unknown" / `null`
  when the answer must come from provided data.
- Classification uses meaningful labels, not arbitrary numeric scores.
- Functions for live data; do not stream a tool-use turn.

## Perplexity / Sonar

Sources: docs.perplexity.ai prompt guide.

- State the research question and the decision the answer should
  support.
- Separate standing citation rules from the one-off entities, dates,
  and constraints.
- Name required or excluded source types, domains, geography, and a
  date window. Convert "latest" into an explicit range.
- Prefer ranked findings with short rationales. When sources are weak,
  say what was not found.

## MiniMax

Sources: platform.minimax.io M-series usage tips.

- Flat labeled sections: task, context, sources, constraints,
  examples, tool policy, output.
- Long sources before the ask, delimited. Extract before synthesizing.
- Lock the answer language when inputs mix languages.
- Preserve the full assistant turn (tool calls and reasoning fields)
  on the next API hop. Stable prefix first for cache.
