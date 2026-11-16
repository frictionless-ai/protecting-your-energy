#!/usr/bin/env python3
"""Read/write local secrets without printing values. Values only via stdin/stdout when explicitly piped to a non-TTY.

Usage:
  secret_io.py list
  secret_io.py path env|creds|tokens|chrome <name>
  secret_io.py put-env KEY          # value on stdin
  secret_io.py put-file creds|tokens RELPATH   # bytes on stdin
"""
from __future__ import annotations

import os
import sys
import re
import shlex
from pathlib import Path

USER_ROOT = Path.home()
SECRETS_ENV = Path(os.environ.get("PYE_SECRETS_ENV", USER_ROOT / ".config" / "secrets.env"))
STATE = Path(os.environ.get("PYE_SECRET_STATE", USER_ROOT / ".local" / "state" / "agent-secrets"))
CREDS = STATE / "creds"
TOKENS = STATE / "tokens"
CHROME = Path(os.environ.get("PYE_CHROME_PROFILES", USER_ROOT / ".local" / "share" / "persona-sessions" / "chrome"))


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _ensure_dirs() -> None:
    for p in (STATE, CREDS, TOKENS, CHROME):
        p.mkdir(parents=True, exist_ok=True)
        os.chmod(p, 0o700)


def cmd_list() -> None:
    """Counts and profile dir names only. Never print secret key names or values."""
    env_n = 0
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text().splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                env_n += 1
    cred_n = len(list(CREDS.glob("*"))) if CREDS.exists() else 0
    tok_n = len(list(TOKENS.glob("*"))) if TOKENS.exists() else 0
    chrome = sorted(p.name for p in CHROME.iterdir() if p.is_dir()) if CHROME.exists() else []
    print("secrets_env", env_n)
    print("cred_files", cred_n)
    print("token_files", tok_n)
    print("chrome_profiles", len(chrome))


def cmd_path(kind: str, name: str) -> None:
    mapping = {
        "env": SECRETS_ENV,
        "creds": CREDS / name,
        "tokens": TOKENS / name,
        "chrome": CHROME / name,
    }
    p = mapping.get(kind)
    if p is None:
        _die("kind must be env|creds|tokens|chrome")
    print(p)


def cmd_put_env(key: str) -> None:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None:
        _die("invalid key")
    if sys.stdin.isatty():
        _die("refuse TTY stdin; pipe the value")
    value = sys.stdin.read().strip("\n")
    if not value:
        _die("empty value")
    _ensure_dirs()
    SECRETS_ENV.parent.mkdir(parents=True, exist_ok=True)
    value = shlex.quote(value)
    lines: list[str] = []
    found = False
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text().splitlines():
            if line.startswith(key + "="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    tmp = SECRETS_ENV.with_suffix(".env.tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(SECRETS_ENV)
    os.chmod(SECRETS_ENV, 0o600)
    print("OK", key)


def cmd_put_file(kind: str, rel: str) -> None:
    if kind not in ("creds", "tokens"):
        _die("kind must be creds|tokens")
    if not rel or Path(rel).name != rel or rel.startswith("."):
        _die("relpath must be a basename")
    if sys.stdin.isatty():
        _die("refuse TTY stdin; pipe the value")
    data = sys.stdin.buffer.read()
    if not data:
        _die("empty value")
    _ensure_dirs()
    dest = (CREDS if kind == "creds" else TOKENS) / rel
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(data)
    os.chmod(tmp, 0o600)
    tmp.replace(dest)
    os.chmod(dest, 0o600)
    print("OK", kind, rel)


def main() -> None:
    if len(sys.argv) < 2:
        _die(__doc__ or "usage")
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "path" and len(sys.argv) >= 3:
        cmd_path(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "put-env" and len(sys.argv) == 3:
        cmd_put_env(sys.argv[2])
    elif cmd == "put-file" and len(sys.argv) == 4:
        cmd_put_file(sys.argv[2], sys.argv[3])
    else:
        _die(__doc__ or "usage")


if __name__ == "__main__":
    main()
