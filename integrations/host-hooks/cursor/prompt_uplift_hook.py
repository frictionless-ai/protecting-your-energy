#!/usr/bin/env python3
"""Prompt-uplift hook: mark, don't rewrite.

Reads a Claude Code UserPromptSubmit or Cursor beforeSubmitPrompt payload
on stdin and either stays silent (or Cursor ``{"continue": true}``) or
emits a fixed, content-free marker.

Design rules (see SKILLS.md Rev. 2 §4):
  - The hook never rewrites the prompt.
  - The hook never spawns agents (recursion guard).
  - The injected marker contains NO user content.
  - Fail open: any error -> exit 0; the turn proceeds.

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import json
import os
import re
import stat
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from prescreen import (  # noqa: E402
    AUTONOMY,
    OPTOUT,
    RAW_PATH,
    RAW_SHELL,
    SLASH,
    is_autonomy_grant_only,
    is_raw_path,
    is_raw_shell,
    is_slash,
    optout_kind,
    unwrap_harness,
)

MARKER = (
    "PROMPT_UPLIFT_CANDIDATE: this user turn may benefit from prompt uplift. "
    "If the task will be delegated, or the message has executor context gaps "
    "(unbound referents, a correction to in-flight work, an artifact dump "
    "without framing, a goal without success conditions), consult the "
    "prompt-uplift skill before acting. If the message is complete for its "
    "executor, ignore this note. This note contains no user content."
)

# Fields that indicate a non-top-level (subagent) session in hook input.
SUBAGENT_FIELDS = (
    "agent_type",
    "agent_name",
    "parent_session_id",
    "subagent",
    "is_subagent",
    "parent_tool_use_id",
)


def state_dir() -> str | None:
    """Return a private state directory, or None if it cannot be used safely.

    Preference: ``PROMPT_UPLIFT_STATE_DIR``, then ``$XDG_RUNTIME_DIR/prompt-uplift``,
    then ``~/.cache/prompt-uplift``. Never defaults to world-writable
    ``/tmp/prompt-uplift``. Created with mode 0o700. Symlinks and directories
    owned by another uid are refused.
    """
    override = os.environ.get("PROMPT_UPLIFT_STATE_DIR")
    if override:
        d = override
    elif os.environ.get("XDG_RUNTIME_DIR"):
        d = os.path.join(os.environ["XDG_RUNTIME_DIR"], "prompt-uplift")
    else:
        d = os.path.join(os.path.expanduser("~"), ".cache", "prompt-uplift")
    return _ensure_private_dir(d)


def _ensure_private_dir(path: str) -> str | None:
    try:
        if os.path.islink(path):
            return None
        if os.path.exists(path):
            st = os.lstat(path)
            if not stat.S_ISDIR(st.st_mode):
                return None
            if st.st_uid != os.getuid():
                return None
        else:
            os.makedirs(path, mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    except OSError:
        return None
    return path


def _safe_session_token(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)[:80]


def optout_path(session_id: str) -> str | None:
    d = state_dir()
    if not d:
        return None
    return os.path.join(d, f"optout-{_safe_session_token(session_id)}")


def suppress_path(session_id: str) -> str | None:
    d = state_dir()
    if not d:
        return None
    return os.path.join(d, f"suppress-{_safe_session_token(session_id)}")


def write_flag(path: str) -> None:
    """Create an empty flag file (never stores prompt text). 0o600 + O_NOFOLLOW."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, b"")
    finally:
        os.close(fd)


def extract_prompt(data: dict) -> str:
    return data.get("prompt") or data.get("message") or ""


def extract_session_id(data: dict) -> str | None:
    raw = data.get("session_id") or data.get("conversation_id")
    if raw is None or raw == "":
        return None
    return str(raw)


def is_cursor_payload(data: dict) -> bool:
    event = (
        data.get("hook_event_name")
        or data.get("event_name")
        or data.get("event")
        or ""
    )
    if event == "beforeSubmitPrompt":
        return True
    if data.get("conversation_id") and not data.get("session_id"):
        return True
    return False


def emit(cursor: bool, mark: bool) -> None:
    if cursor:
        payload: dict = {"continue": True}
        if mark:
            payload["additional_context"] = MARKER
        print(json.dumps(payload))
        return
    if mark:
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
    prompt = unwrap_harness(extract_prompt(data))
    session_id = extract_session_id(data)
    cursor = is_cursor_payload(data)

    for field in SUBAGENT_FIELDS:
        if data.get(field):
            emit(cursor, mark=False)
            return 0

    if session_id:
        sp = suppress_path(session_id)
        if sp and os.path.exists(sp):
            emit(cursor, mark=False)
            return 0

    if "PROMPT_UPLIFT_CANDIDATE" in prompt:
        emit(cursor, mark=False)
        return 0

    if session_id:
        op = optout_path(session_id)
        if op and os.path.exists(op):
            emit(cursor, mark=False)
            return 0

    # Opt-out before any other classification. Quoted / interrogative
    # matches must not persist a session flag.
    kind = optout_kind(prompt)
    if kind == "sticky":
        if session_id:
            op = optout_path(session_id)
            if op:
                try:
                    write_flag(op)
                except OSError:
                    pass
        emit(cursor, mark=False)
        return 0

    if is_slash(prompt) or is_raw_path(prompt) or is_raw_shell(prompt):
        emit(cursor, mark=False)
        return 0
    if is_autonomy_grant_only(prompt):
        emit(cursor, mark=False)
        return 0
    if not prompt.strip():
        emit(cursor, mark=False)
        return 0

    emit(cursor, mark=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Fail open: uplift is an optimization, never a gate.
        print(f"prompt-uplift hook: {exc}", file=sys.stderr)
        sys.exit(0)
