# Semantic Expression

The `UserPromptSubmit` hook asks the assistant to recover relevant context before
interpreting a message and continue the authorized request. Rewritten prompts and
phrasing coaching are provided when requested. The assistant uses the current
conversation, named material, corrections and recovered original context.
The script requires Python 3 and sends no network requests or transcript logs.

The hook output is delivered as developer context. Codex also retains the
original user message. Its submit-hook protocol offers context injection and
blocking, with no user-message replacement field.
See the [Codex hook protocol](https://learn.chatgpt.com/docs/hooks).

Host installation should reconcile any existing direct registration with the
plugin route so each event runs the hook once. Enable and trust the command when
the host requires it, then verify delivery in a fresh chat.

Say the thought clearly, with its meaning intact.

`make-coherent` develops rough explanations for their audience. It recovers
missing connections, preserves conditions and uncertainty, and uses accurate
terminology when it represents the intended mechanism.

`contextual-reply` writes the relevant next message in a conversation, using
earlier reasoning where it helps the present move. Extra context stays optional.
Drafting and sending remain separate actions.

Both skills retrieve personal examples from the relevant context instead of
imposing a fixed register. The agent keeps source and meaning checks privately;
the reader receives the requested artifact. See [methods](references/methods.md).

Protect Your Energy can invoke these capabilities alongside reconstruction,
prioritization and continuity. Each capability has one canonical skill body.
