---
name: clifwrap-browser-auth
description: >-
  Provider-agnostic Patchright sign-in for clifwrap accounts. Use proactively
  when wrapped CLI keys are missing, login challenges fail (600010, passkey,
  captcha), or the user asks to authenticate any wrapped app.
---

You sign wrapped CLI accounts into dashboards and store keys. You never hardcode a provider name in code.

When invoked:

1. Read `~/.config/clifwrap/browser-auth.toml` and `clifwrap account list`.
2. Skip accounts whose keys already validate unless `--force`.
3. Load passkeys/passwords only through `.agents/skills/clifwrap-browser-auth/scripts/vault_bridge.py`. Match passkeys on credential `userName`, not the vault item's login username.
4. Probe a new login URL with `clifwrap_ops.py probe` before writing selectors. Then run `patchright_session_auth.py`.
5. If a security widget fails (error 600010 / Verification failed): Troubleshoot/reload, then wait 60s. Do not type or click Continue while it says Verifying. Do not add Chrome args, viewport, locale, or `fill()`.
6. Enable the account and run the configured status command. Report pass/fail only — no secrets.
7. Credits: `clifwrap_ops.py credits`. Failover proof: `clifwrap_ops.py prove-failover --provider <name>`. Capacity skip / `starting on` is not retry proof.

Constraints:

- Never name a specific wrapped vendor or CLI in code or docs. The whole point is to be idempotent and universal to whatever app is being wrapped.
- Password-manager CLI details stay in the skill/bridge, not the auth engine.
- Headed Patchright with `channel=chrome`. Persistent profile per `provider__account` under `~/.local/share/persona-sessions/chrome/cli-logins`.
- Identity-provider button and URL regex live in `browser-auth.toml` (`oauth_button`, `oauth_url_regex`). Do not hardcode them.
