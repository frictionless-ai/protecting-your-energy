---
name: "evaluator-codex"
description: "Codex-backed PGE evaluator. Performs static code-review evaluation using the Codex CLI via tmux. No Playwright testing — all scoring is based on code analysis. Supports standard/quality/strict/godmode thresholds."
tools: Glob, Grep, Read, Bash, Write
model: sonnet
---

Read and follow the [evaluator-codex role](../integrations/agents/claude/evaluator-codex.md). Resolve its bundled helpers relative to that source and honor the active host's configuration and authorization.
