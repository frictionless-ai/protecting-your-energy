#!/usr/bin/env bash
# Restore a live game tree from a checkpoint git SHA. Default is dry-run.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/restore-checkpoint.sh --checkpoint-dir DIR --sha SHA --game DIR [--dry-run|--confirm]

Restores the live game tree from .modsync/checkpoints. Default is --dry-run.

Options:
  --checkpoint-dir DIR  Path to <game>/.modsync/checkpoints
  --sha SHA             Last good commit
  --game DIR            Live game tree (rsync target)
  --dry-run             Print planned commands only (default)
  --confirm             Perform checkout, clean, and rsync
  --help                Show this help

Exit codes:
  0  success
  2  restore finished but appearance.2da is 0 bytes
  3  bad arguments or missing paths
EOF
}

CK=""
SHA=""
GAME=""
CONFIRM=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --checkpoint-dir) CK="${2:-}"; shift 2 ;;
    --sha) SHA="${2:-}"; shift 2 ;;
    --game) GAME="${2:-}"; shift 2 ;;
    --dry-run) CONFIRM=0; shift ;;
    --confirm) CONFIRM=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Error: unknown argument '$1'. See --help." >&2; exit 3 ;;
  esac
done

if [[ -z "$CK" || -z "$SHA" || -z "$GAME" ]]; then
  echo "Error: --checkpoint-dir, --sha, and --game are required. See --help." >&2
  exit 3
fi
if [[ ! -d "$CK/.git" && ! -d "$CK" ]]; then
  echo "Error: checkpoint dir not found: $CK" >&2
  exit 3
fi
if [[ ! -d "$GAME" ]]; then
  echo "Error: game dir not found: $GAME" >&2
  exit 3
fi

echo "git -C $CK checkout -f $SHA"
echo "git -C $CK clean -fd"
echo "rsync -a --delete --exclude .modsync/ --exclude .git/ $CK/ $GAME/"

if [[ "$CONFIRM" -eq 0 ]]; then
  echo '{"ok": true, "mode": "dry-run"}'
  exit 0
fi

git -C "$CK" checkout -f "$SHA"
git -C "$CK" clean -fd
rsync -a --delete --exclude '.modsync/' --exclude '.git/' "$CK/" "$GAME/"

APPEAR="$GAME/Override/appearance.2da"
if [[ -f "$APPEAR" ]]; then
  SIZE=$(wc -c < "$APPEAR" | tr -d ' ')
  echo "{\"appearance_bytes\": $SIZE}"
  if [[ "$SIZE" -eq 0 ]]; then
    echo "Error: Override/appearance.2da is 0 bytes after restore. Abort. Check git cat-file -s ${SHA}:Override/appearance.2da" >&2
    exit 2
  fi
fi

echo '{"ok": true, "mode": "confirm"}'
exit 0
