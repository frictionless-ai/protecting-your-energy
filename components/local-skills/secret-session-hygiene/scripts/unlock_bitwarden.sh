#!/usr/bin/env bash
# Unlock Bitwarden using BITWARDEN_MASTER_PASSWORD from the child environment.
# Never prints the password or BW_SESSION.
set -euo pipefail

SECRET_IO="$(dirname "$0")/secret_io.py"
ENSURE="$(dirname "$0")/ensure_bitwarden.sh"

if [[ -z "${BITWARDEN_MASTER_PASSWORD:-}" ]]; then
  echo '{"ok":false,"error_class":"missing-env"}'
  exit 1
fi

if ! command -v bw >/dev/null 2>&1; then
  echo '{"ok":false,"error_class":"bw-missing"}'
  exit 1
fi

err="$(mktemp "${XDG_RUNTIME_DIR:-/tmp}/bw-unlock.XXXXXX")"
tmp="$(mktemp "${XDG_RUNTIME_DIR:-/tmp}/bw-session.XXXXXX")"
chmod 600 "$err" "$tmp"
# --passwordenv keeps the secret off argv. --raw must not reach the terminal.
if ! bw unlock --passwordenv BITWARDEN_MASTER_PASSWORD --raw >"$tmp" 2>"$err"; then
  rm -f "$tmp" "$err"
  echo '{"ok":false,"error_class":"unlock-failed"}'
  exit 2
fi

python3 "$SECRET_IO" put-file tokens bw.session <"$tmp" >/dev/null
export BW_SESSION
BW_SESSION="$(cat "$tmp")"
rm -f "$tmp" "$err"
# Status only. Do not echo BW_SESSION.
"$ENSURE"
