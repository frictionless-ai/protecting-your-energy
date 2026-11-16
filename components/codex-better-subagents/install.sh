#!/usr/bin/env bash
# Install the routing guide and worker definitions into your home directory.
# Existing files that differ are backed up with a timestamped .bak suffix before being replaced.
set -euo pipefail

case "${1:-}" in
  --help|-h)
    echo "Usage: install.sh [--apply]"
    echo "Default previews files. --apply installs user-wide worker profiles with backups."
    exit 0
    ;;
  --apply) apply=true ;;
  "") apply=false ;;
  *) echo "Unknown argument: $1" >&2; exit 2 ;;
esac
if [[ "$#" -gt 1 ]]; then
  echo "Expected at most one option" >&2
  exit 2
fi

stamp="$(date +%Y%m%d-%H%M%S)"
src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install_file() {
  local from="$1" to="$2"
  if [[ "$apply" == false ]]; then
    echo "would install $from -> $to"
    return
  fi
  mkdir -p "$(dirname "$to")"
  if [[ -e "$to" ]] && ! cmp -s "$from" "$to"; then
    cp "$to" "$to.bak.$stamp"
    echo "backed up $to -> $to.bak.$stamp"
  fi
  cp "$from" "$to"
  echo "installed $to"
}

install_file "$src/ROUTING.md" "$HOME/.agents/rules/subagent-model-routing.md"
for f in "$src"/agents/claude/*.md; do
  install_file "$f" "$HOME/.claude/agents/$(basename "$f")"
done
for f in "$src"/agents/codex/*.toml; do
  install_file "$f" "$HOME/.codex/agents/$(basename "$f")"
done
install_file "$src/codex/worker.config.toml" "$HOME/.codex/worker.config.toml"

echo
if [[ "$apply" == true ]]; then
  echo "Installed. Review the selected model routes in your host configuration."
else
  echo "Preview complete. --apply explicitly installs the displayed user-wide files."
fi
