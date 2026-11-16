# Target-model routing

This directory is subject matter: current model names belong here and
nowhere in skill or agent instruction surfaces.

The optional first argument to `/prompt-optimizer` is a **downstream**
model the compiled prompt should be optimized for. It is not the
executing model's `model:` frontmatter.

## How to route

1. Take the first whitespace-separated token of the argument string.
2. Normalize: lowercase; strip org prefixes
   (`openai/`, `google/`, `xai/`, `qwen/`, `deepseek-ai/`,
   `meta-llama/`, `mistralai/`, `cohere/`, `anthropic/`,
   `moonshot/`, `zai/`, `aws/`, `amazon/`, `microsoft/`,
   `ai21/`, `perplexity/`, `minimax/`).
3. Match the first row in the table below.
4. If nothing matches, or the token is missing, or the token is
   `generic` / `auto` / `default`: use [generic.md](generic.md) and say
   so. Do not invent family-specific rules.
5. The remainder of the argument string is the user's prompt. If the
   first token did not match, the **entire** argument string is the
   prompt (an unknown model name is not stripped).

## Alias table

| Pattern (substring / prefix after normalize) | File |
|---|---|
| `fable`, `mythos`, `opus`, `sonnet`, `haiku`, `claude` | [anthropic.md](anthropic.md) |
| `gpt-5`, `gpt-4.1`, `gpt-4o`, `o1`, `o3`, `o4`, `codex` | [openai.md](openai.md) |
| `gemini`, `gemma` | [google.md](google.md) |
| `mistral`, `magistral`, `devstral`, `pixtral`, `ministral`, `codestral` | [others.md](others.md) (Mistral) |
| `deepseek` | [others.md](others.md) (DeepSeek) |
| `grok` | [others.md](others.md) (xAI) |
| `llama` | [others.md](others.md) (Meta; 2025 vintage) |
| `command-a`, `command-r` | [others.md](others.md) (Cohere) |
| `qwen` | [others.md](others.md) (Qwen) |
| `kimi`, `moonshot` | [others.md](others.md) (Kimi) |
| `glm` | [others.md](others.md) (GLM) |
| `nova` | [others.md](others.md) (Nova) |
| `phi` | [others.md](others.md) (Phi) |
| `jamba` | [others.md](others.md) (Jamba) |
| `sonar`, `perplexity` | [others.md](others.md) (Perplexity) |
| `minimax` | [others.md](others.md) (MiniMax) |
| anything else | [generic.md](generic.md) |

Current ids observed 2026-08-13 (do not treat as exhaustive):

- Anthropic: `claude-fable-5`, `claude-opus-5`, `claude-sonnet-5`
- OpenAI: `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`
- Gemini: `gemini-3.5-flash`, `gemini-3.1-pro`
- Mistral: `mistral-small-latest`, `mistral-medium-3-5`
- DeepSeek: `deepseek-v4-flash`, `deepseek-v4-pro`
- xAI: `grok-4.6`, `grok-4.20-multi-agent`
- Cohere: `command-a-plus-05-2026`
- Qwen: `Qwen3-*` and Alibaba `qwen3.5`–`qwen3.8` series
- Llama: `Llama-4-Scout`, `Llama-4-Maverick` (2025-04 format)
- Kimi / Moonshot, GLM, Nova, Phi, Jamba, Perplexity Sonar, MiniMax M-series:
  routed through [others.md](others.md)

## Effort knobs

Reasoning depth is host configuration (`effort`, `reasoning.effort`,
`thinking_level`, `reasoning_effort`, `enable_thinking`). Family files
may say “if the host exposes X, set Y.” Do not write “think hard” into
the compiled prompt.
