#!/usr/bin/env python3
"""Password-manager bridge. Auth engine talks only to this process.

Backends are selected by CLIFWRAP_VAULT_BACKEND (default: session CLI).
Never print secret values. Metadata and temp-file paths only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

STATE_HOME = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
SESSION_FILE = Path(os.environ.get("CLIFWRAP_VAULT_SESSION_FILE") or STATE_HOME / "agent-secrets/tokens/bw.session").expanduser()


def _session_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("CLIFWRAP_VAULT_SESSION"):
        return env
    if SESSION_FILE.exists():
        env["BW_SESSION"] = SESSION_FILE.read_text().strip()
        env["CLIFWRAP_VAULT_SESSION"] = env["BW_SESSION"]
    return env


def _cli(*args: str) -> str:
    exe = os.environ.get("CLIFWRAP_VAULT_BIN", "bw")
    return subprocess.check_output([exe, *args], env=_session_env(), text=True)


def _items() -> list[dict]:
    return json.loads(_cli("list", "items"))


def _match_passkey(email: str, rp: str) -> dict | None:
    email_l = email.lower()
    for it in _items():
        login = it.get("login") or {}
        for cred in login.get("fido2Credentials") or []:
            uname = (cred.get("userName") or login.get("username") or "").lower()
            rp_id = cred.get("rpId") or ""
            rp_ok = (not rp) or rp_id == rp or rp_id.endswith("." + rp) or rp.endswith(rp_id)
            if uname == email_l and rp_ok:
                return cred
    return None


def _to_cdp(cred: dict) -> dict:
    cid = cred["credentialId"]
    try:
        cred_bytes = uuid.UUID(cid).bytes
    except Exception:
        pad = cid + "=" * ((4 - len(cid) % 4) % 4)
        cred_bytes = base64.urlsafe_b64decode(pad)
    key_raw = cred["keyValue"]
    pad = key_raw + "=" * ((4 - len(key_raw) % 4) % 4)
    try:
        pkcs8 = base64.urlsafe_b64decode(pad)
    except Exception:
        pkcs8 = base64.b64decode(pad)
    uh = cred.get("userHandle") or ""
    try:
        uh_bytes = base64.b64decode(uh + "=" * ((4 - len(uh) % 4) % 4))
        uh_b64 = base64.b64encode(uh_bytes).decode()
    except Exception:
        uh_b64 = uh
    return {
        "credentialId": base64.b64encode(cred_bytes).decode(),
        "isResidentCredential": True,
        "rpId": cred.get("rpId") or "",
        "privateKey": base64.b64encode(pkcs8).decode(),
        "userHandle": uh_b64,
        "signCount": int(cred.get("counter") or 0),
    }


def cmd_has_passkey(email: str, rp: str) -> None:
    print(json.dumps({"ok": bool(_match_passkey(email, rp))}))


def cmd_passkey_cdp(email: str, rp: str) -> None:
    cred = _match_passkey(email, rp)
    if not cred:
        print(json.dumps({"ok": False}))
        raise SystemExit(1)
    fd, path = tempfile.mkstemp(prefix="vault-passkey-", suffix=".json")
    os.close(fd)
    dest = Path(path)
    dest.write_text(json.dumps(_to_cdp(cred)))
    os.chmod(dest, 0o600)
    print(json.dumps({"ok": True, "path": str(dest)}))


def cmd_password(email: str, uri: str) -> None:
    email_l = email.lower()
    for it in _items():
        login = it.get("login") or {}
        user = (login.get("username") or "").lower()
        uris = " ".join(u.get("uri") or "" for u in (login.get("uris") or []))
        if user == email_l and (not uri or uri in uris) and login.get("password"):
            fd, path = tempfile.mkstemp(prefix="vault-pass-", suffix=".txt")
            os.close(fd)
            Path(path).write_text(login["password"])
            os.chmod(path, 0o600)
            print(json.dumps({"ok": True, "path": path, "has_totp": bool(login.get("totp"))}))
            return
    print(json.dumps({"ok": False}))
    raise SystemExit(1)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("has-passkey", "passkey-cdp", "password"))
    p.add_argument("--email", required=True)
    p.add_argument("--rp", default="")
    p.add_argument("--uri", default="")
    args = p.parse_args()
    try:
        if args.action == "has-passkey":
            cmd_has_passkey(args.email, args.rp)
        elif args.action == "passkey-cdp":
            cmd_passkey_cdp(args.email, args.rp)
        else:
            cmd_password(args.email, args.uri)
    except subprocess.CalledProcessError:
        print(json.dumps({"ok": False, "error": "vault-locked"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
