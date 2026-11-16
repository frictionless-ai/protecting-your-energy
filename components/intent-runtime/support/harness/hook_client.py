"""Invoke the UserPromptSubmit / beforeSubmitPrompt hook and parse JSON."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "prompt_uplift_hook.py"
CURSOR_HOOK = REPO / "integrations" / "cursor-project" / ".cursor" / "hooks" / "prompt_uplift_hook.py"


def run_hook(
    prompt: str,
    session_id: str = "eval",
    extra: dict | None = None,
    state_dir: str | None = None,
    *,
    cursor: bool = False,
    hook_path: Path | None = None,
    omit_session: bool = False,
) -> dict | None:
    """Return the hook JSON object, or None if the hook stayed silent."""
    if cursor:
        payload: dict = {
            "conversation_id": session_id,
            "hook_event_name": "beforeSubmitPrompt",
            "message": prompt,
        }
    else:
        payload = {
            "session_id": session_id,
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        }
    if omit_session:
        payload.pop("session_id", None)
        payload.pop("conversation_id", None)
    if extra:
        payload.update(extra)
    env = os.environ.copy()
    if state_dir:
        env["PROMPT_UPLIFT_STATE_DIR"] = state_dir
    script = hook_path or (CURSOR_HOOK if cursor else HOOK)
    proc = subprocess.run(
        ["python3", str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"hook failed ({proc.returncode}): {proc.stderr}")
    out = proc.stdout.strip()
    if not out:
        return None
    return json.loads(out)


def hook_marked(result: dict | None) -> bool:
    if not result:
        return False
    ctx = (
        (result.get("hookSpecificOutput") or {}).get("additionalContext")
        or result.get("additional_context")
        or ""
    )
    return "PROMPT_UPLIFT_CANDIDATE" in ctx
