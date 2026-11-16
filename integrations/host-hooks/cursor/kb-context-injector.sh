#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
prompt="$(printf '%s' "$input" | jq -r '.prompt // .input // .text // empty')"

if [[ "$prompt" =~ [Kk]nowledge[[:space:]]?[Bb]ase|[Kk][Bb]|[Rr]esearch|docs/ ]]; then
  echo '{"permission":"allow","agent_message":"Knowledgebase context: prefer build-knowledgebase or research-with-evidence skills and keep evidence labels explicit."}'
else
  echo '{"permission":"allow"}'
fi
