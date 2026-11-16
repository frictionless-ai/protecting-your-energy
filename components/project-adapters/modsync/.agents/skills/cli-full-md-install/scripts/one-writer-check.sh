#!/usr/bin/env bash
# Fail if another process already has the game tree open for install.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/one-writer-check.sh --game DIR [--allow-pid PID]

Exit 0 if no other install process mentions DIR.
Exit 2 if another writer is found.
Exit 3 on bad arguments.

Options:
  --game DIR       Live game tree (required)
  --allow-pid PID  Ignore this PID (the process you are about to start)
  --help           Show this help

Example:
  bash scripts/one-writer-check.sh --game $MODSYNC_HOT_ROOT/K1_auto
EOF
}

GAME=""
ALLOW=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --game) GAME="${2:-}"; shift 2 ;;
    --allow-pid) ALLOW="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Error: unknown argument '$1'. See --help." >&2; exit 3 ;;
  esac
done

if [[ -z "$GAME" ]]; then
  echo "Error: --game is required. See --help." >&2
  exit 3
fi

# Resolve for substring match against argv.
GAME_ABS="$(readlink -f "$GAME" 2>/dev/null || echo "$GAME")"

hits=0
# pgrep -a prints pid + command. Do not use mtime.
while read -r pid cmd; do
  [[ -z "${pid:-}" ]] && continue
  if [[ -n "$ALLOW" && "$pid" == "$ALLOW" ]]; then
    continue
  fi
  if [[ "$cmd" == *"$GAME"* || "$cmd" == *"$GAME_ABS"* ]]; then
    echo "{\"pid\": $pid, \"cmd\": $(printf '%s' "$cmd" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" 
    hits=$((hits + 1))
  fi
done < <(pgrep -a -f 'ModSync.Core|dotnet exec' 2>/dev/null || true)

if [[ "$hits" -gt 0 ]]; then
  echo "Error: $hits writer(s) already mention --game path. Do not start a second writer." >&2
  exit 2
fi

echo "{\"ok\": true, \"game\": $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$GAME_ABS")}"
exit 0
