"""Hosted inference via the locally installed Claude CLI.

Prompts leave this machine. This is NOT local model inference.

`env -u CLAUDECODE` is required: nested claude invocations refuse to run
inside a Claude Code session unless that variable is unset.
"""
import json
import subprocess


class LLMError(RuntimeError):
    pass


def ask(prompt, timeout=300):
    """Run `env -u CLAUDECODE claude -p <prompt> --output-format json` and
    return the result text. Raises LLMError on any failure so callers can
    fall back to heuristics."""
    cmd = ["env", "-u", "CLAUDECODE", "claude", "-p", "--safe-mode",
           "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence",
           "--output-format", "json"]
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise LLMError(str(e))
    if proc.returncode != 0:
        raise LLMError("claude exited %d: %s" % (proc.returncode, proc.stderr[:500]))
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        raise LLMError("claude output was not JSON")
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, str):
        raise LLMError("claude JSON had no result field")
    return result


def ask_json(prompt, timeout=300):
    """ask(), then parse the first JSON value found in the reply."""
    text = ask(prompt, timeout=timeout)
    # Models often wrap JSON in a code fence or prose; find the first bracket.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                continue
    raise LLMError("no JSON found in claude reply")
