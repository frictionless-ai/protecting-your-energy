#!/usr/bin/env bash
# Run a command with ~/.config/secrets.env loaded. Does not echo values.
set -euo pipefail
ENV_FILE="${PYE_SECRETS_ENV:-${HOME}/.config/secrets.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing ${ENV_FILE}" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
exec "$@"
