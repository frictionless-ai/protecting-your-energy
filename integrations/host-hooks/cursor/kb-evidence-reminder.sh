#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
path="$(printf '%s' "$input" | jq -r '.path // .file_path // .target_file // empty')"

if [[ "$path" =~ (^|/)docs/.*\.md$ ]] || [[ "$path" =~ (^|/)knowledgebase/.*\.md$ ]]; then
  echo '{"additional_context":"Evidence reminder: label claims with [REPO]/[UI]{public|auth}/[OFFICIAL]/[SYNTH]/[OPEN] and date external research when recency matters."}'
else
  echo '{}'
fi
