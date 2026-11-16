# Prompt-submit guidance

`hooks/intent_coach.py` is the locally developed intent and phrasing hook retained
by Protect Your Energy. It handles nonempty `UserPromptSubmit` events and returns
fixed context-recovery instructions through `hookSpecificOutput.additionalContext`.

The assistant receives guidance to recover the current request, inspect relevant
original context when necessary, preserve constraints and continue authorized
work. Rewritten prompts and phrasing coaching are provided when requested.

The hook uses Python 3's standard library. It makes no network requests, launches
no model and writes no transcript logs. The host retains the original user
message. Model-mediated prompt compilation is supplied by the intent-runtime
and prompt-uplift skills during the assistant's turn.

The root plugin registers this hook through `hooks/energy.py`. Existing direct
registrations should be reconciled when enabling that route so it runs once.
Host event support, trust and actual delivery require verification in the target
installation.
