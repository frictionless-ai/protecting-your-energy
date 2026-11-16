#!/usr/bin/env python3
"""Prompt-uplift UserPromptSubmit hook: mark, don't rewrite.

Reads the Claude Code UserPromptSubmit hook payload on stdin and either:
  - emits nothing (protected / opted-out / non-top-level turn), or
  - emits hook JSON whose additionalContext is a fixed, content-free marker
    telling the agent this turn may benefit from the prompt-uplift skill.

Design rules (see SKILLS.md Rev. 2 §4):
  - The hook never rewrites the prompt (UserPromptSubmit cannot replace it).
  - The hook never spawns agents (recursion guard).
  - The injected marker contains NO user content (it is persisted in session
    transcripts by the harness).
  - Fail open: any error -> exit 0 with no output; the turn proceeds.

Stdlib only. No third-party dependencies.
"""

import json
import os
import re
import sys

MARKER = (
    "PROMPT_UPLIFT_CANDIDATE: this user turn may benefit from prompt uplift. "
    "If the task will be delegated, or the message has executor context gaps "
    "(unbound referents, a correction to in-flight work, an artifact dump "
    "without framing, a goal without success conditions), consult the "
    "prompt-uplift skill before acting. If the message is complete for its "
    "executor, ignore this note. This note contains no user content."
)

OPTOUT_PATTERNS = re.compile(
    r"(stop|don'?t|do not|quit)\s+(rewriting|uplifting|optimi[sz]ing)\s+(my\s+)?(prompts?|messages?)",
    re.IGNORECASE,
)

# Protected classes: deterministic pre-screen (SKILLS.md Rev. 2 §3, §4).
SLASH_COMMAND = re.compile(r"^\s*/\S")
RAW_PATH = re.compile(r"^\s*(~?/|\./)\S+\s*$")
RAW_SHELL = re.compile(
    r"^\s*(?:(?:cd|ls|cat|git|python3?|pip3?|npm|npx|cargo|docker|kubectl|ssh|curl|wget)\b\S*\s+\S|make\s+(?!it\b|this\b|that\b|them\b|me\b|sure\b)\S)"
)

# Fields that indicate a non-top-level (subagent) session in hook input.
# Names vary across harness versions; checked permissively. See
# IMPLEMENTATION-NOTES.md.
SUBAGENT_FIELDS = ("agent_type", "agent_name", "parent_session_id", "subagent", "is_subagent", "parent_tool_use_id")


def state_dir() -> str:
    base = (
        os.environ.get("PROMPT_UPLIFT_STATE_DIR")
        or os.environ.get("XDG_RUNTIME_DIR")
        or "/tmp"
    )
    d = os.path.join(base, "prompt-uplift")
    os.makedirs(d, exist_ok=True)
    return d


def optout_path(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:80]
    return os.path.join(state_dir(), f"optout-{safe}")


def suppress_path(session_id: str) -> str:
    # The uplift skill (or a wrapper) may create this file while uplift runs,
    # so hook-visible turns generated during uplift are never re-marked.
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:80]
    return os.path.join(state_dir(), f"suppress-{safe}")


def emit_marker() -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": MARKER,
                }
            }
        )
    )


def main() -> int:
    data = json.load(sys.stdin)
    prompt = data.get("prompt") or ""
    session_id = str(data.get("session_id") or "unknown")

    # Recursion / non-top-level guard.
    for field in SUBAGENT_FIELDS:
        if data.get(field):
            return 0
    if os.path.exists(suppress_path(session_id)):
        return 0
    # Loop guard: never re-mark text that already carries the marker.
    if "PROMPT_UPLIFT_CANDIDATE" in prompt:
        return 0

    # Session opt-out.
    if os.path.exists(optout_path(session_id)):
        return 0
    if OPTOUT_PATTERNS.search(prompt):
        try:
            with open(optout_path(session_id), "w") as fh:
                fh.write("")  # never store prompt text
        except OSError:
            pass
        return 0

    # Protected classes: pass through with no marker.
    if SLASH_COMMAND.match(prompt) or RAW_PATH.match(prompt) or RAW_SHELL.match(prompt):
        return 0
    if not prompt.strip():
        return 0

    emit_marker()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open: uplift is an optimization, never a gate.
        sys.exit(0)
