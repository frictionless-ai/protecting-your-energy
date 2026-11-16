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
