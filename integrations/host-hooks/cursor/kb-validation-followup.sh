#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
agent_type="$(printf '%s' "$input" | jq -r '.subagent_type // .subagent // .name // empty')"

if [[ "$agent_type" =~ kb-orchestrator|vertical-slice-executor ]]; then
  echo '{"followup_message":"Run the narrowest validation ladder before completion and distinguish landed vs partial vs next."}'
else
  echo '{}'
fi
