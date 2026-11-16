---
name: clifwrap-browser-auth
description: >-
  Signs wrapped CLI accounts into provider dashboards with Patchright, vault
  passkeys, and a 60s human wait on challenges. Use when clifwrap accounts lack
  keys, login pages fail (Turnstile 600010, recaptcha, passkey), or the user
  asks to auth, wrap, or harvest API keys for any wrapped app.
---

This optional adapter uses the external checkout selected by `PYE_CLIFWRAP_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# clifwrap browser auth

Never name a specific wrapped vendor or CLI in code or docs. The whole point is to be idempotent and universal to whatever app is being wrapped.

## When to use

- A wrapped CLI account is disabled or has an empty env key
- A login page is stuck on a security challenge
- The user asks to sign in, harvest keys, or enable clifwrap accounts

## Rules

- Drive Patchright with the official recipe only: `channel="chrome"`, `headless=False`, `no_viewport=True`. Do not set viewport, locale, timezone, user-agent, or extra Chrome args (those leak).
- Do not `fill()` identifiers and do not attach CDP until the bot-check is gone. Type with `keyboard.type(..., delay=75)`. Never click Continue while the widget says Verifying.
- Read targets from `~/.config/clifwrap/browser-auth.toml`. Do not hardcode provider names, login URLs, key prefixes, or identity-provider hosts in Python. `oauth_button` and `oauth_url_regex` live in that table.
- Vault material only via [scripts/vault_bridge.py](scripts/vault_bridge.py). Do not call a password-manager CLI from the auth engine. Do not print secrets.
- Skip accounts whose key already validates (`--force` to redo).
- On a bot-check failure (widget missing, **error 600010**, "Verification failed"): Troubleshoot / reload, then wait **60s** for the user.
- Fill the identifier only after the challenge widget is ready. Prefer OAuth when a passkey exists.
- After a key lands: `secret_io.py put-env`, `clifwrap account enable`, then the provider `--status` / a tiny live call.

## Run

```bash
python3 scripts/browser-auth/patchright_session_auth.py
python3 scripts/browser-auth/clifwrap_ops.py credits
python3 scripts/browser-auth/clifwrap_ops.py probe --login-url "$LOGIN_URL"
python3 scripts/browser-auth/clifwrap_ops.py prove-failover --provider "$PROVIDER"
```

## Traps that burned a full session (do not repeat)

1. **Capacity skip is not retry proof.** Setting the default to an empty account still starts on a healthy one when `proactive_pick` + `capacity_control` are on. Real proof is stderr `failed (matched retry pattern: …); retrying with`. `prove-failover` forces the first call onto the lowest-credit account, then restores config.
2. **Do not "improve" the Patchright launch.** Extra viewport, locale, timezone, or Chrome args, plus `fill()` and typing during Verifying, produce widget error 600010 / a spinner that never finishes.
3. **Probe the login page before writing selectors.** Default view may be Sign Up. The identifier may be `input#username` (text), not `type=email`.
4. **Vault passkeys match `userName` on the credential**, which can differ from the login item's username.
5. **Do not attach CDP until the bot-check page is gone.**
6. **Always restore** clifwrap config/default after a prove-failover run (the script does this in `finally`).

Compatibility entry: `~/.local/state/clifwrap/patchright_bw_passkey_auth.py` (same engine, no provider names).

Learning (why these traps exist): `docs/solutions/workflow-issues/clifwrap-generic-auth-and-failover-proof.md`

## Vault

Default backend is the local password-manager CLI session at `~/.local/state/agent-secrets/tokens/bw.session`. Override with `CLIFWRAP_VAULT_BIN` / `CLIFWRAP_VAULT_SESSION`. Unlock in-process; never put the session on argv.

## Probe a new provider

Dump buttons, inputs, frames (no secrets), then add a `[providers.<name>.browser_auth]` table. Identifier may be `input#username` (text), not `type=email`.
