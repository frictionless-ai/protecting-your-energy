---
name: secret-session-hygiene
description: Reuse authorized local browser sessions and secret-manager credentials without exposing secrets in prompts, logs or command arguments.
---

# Secret session hygiene

Use existing authorized sessions and private configuration to avoid repeated logins. Select the identity from current task context or an authorized private profile. Keep service-specific accounts, browser paths and credentials outside the plugin.

## Handling

Keep passwords, session tokens, cookies and TOTP values out of model-visible output, argv, commits and task packets. Transfer values through protected local files, stdin or a child environment. Read secret values only inside local programs that return status. Avoid screenshots and traces on secret-bearing pages.

Use a configured password manager. Preserve browser windows, active identities and profile locks. Reauthentication requiring human interaction remains with the user while independent authorized work continues. Follow the current task's authorization for installing tools, authenticating, changing access or submitting forms.

## Helpers

- `python3 <skill-directory>/scripts/secret_io.py list` reports counts only.
- `put-env KEY` receives a value through stdin. `put-file creds|tokens BASENAME` stores stdin bytes in private state.
- `run-with-secrets.sh COMMAND...` loads a trusted local shell environment into a child process. `PYE_SECRETS_ENV` selects the file.
- `ensure_bitwarden.sh` returns readiness without account identifiers. `unlock_bitwarden.sh` uses `BITWARDEN_MASTER_PASSWORD` in the child environment and persists the returned session privately.

Set `PYE_SECRET_STATE`, `PYE_SECRETS_ENV` and `PYE_CHROME_PROFILES` for storage roots. Defaults use the user's private application configuration and state directories. Helpers are invoked only when required for the authorized task.

Browser snapshots and service-specific login recipes remain in the original private configuration. Never restore or copy into a live browser profile. Configure the approved browser and identity externally. The portable bundle does not activate host integrations or install credentials.
