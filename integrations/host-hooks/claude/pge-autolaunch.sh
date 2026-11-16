#!/bin/sh
# Optional local PGE bridge notifier. Requires an explicitly configured bridge.
set -u

input=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
prompt=$(printf '%s' "$input" | jq -r '.prompt // ""' 2>/dev/null) || exit 0
printf '%s' "$prompt" | grep -qE '^[[:space:]]*/(pge|pge-strict|pge-quality|pge-ultra|pge-idontcaretokenanymore|pge-god|pge-orchestrator)([[:space:]]|$)' || exit 0

bridge_root=${PYE_PGE_PLUGIN_ROOT:-}
[ -n "$bridge_root" ] || exit 0
command -v node >/dev/null 2>&1 || exit 0
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
[ -n "$cwd" ] || cwd=$PWD

if [ -f "$bridge_root/bridge/pge-notify.cjs" ]; then
  node "$bridge_root/bridge/pge-notify.cjs" "$cwd" >/dev/null 2>&1 &
fi

# Opening an indicator window is opt-in. Pass paths as argv, never interpolate
# hook input into AppleScript or a shell command.
if [ "${PYE_PGE_OPEN_TERMINAL:-0}" = 1 ] &&
   [ -f "$bridge_root/bridge/pge-indicator.cjs" ] &&
   command -v osascript >/dev/null 2>&1; then
  osascript - "$bridge_root/bridge/pge-indicator.cjs" "$cwd" >/dev/null 2>&1 <<'APPLESCRIPT'
on run argv
  tell application "Terminal"
    activate
    do script "node " & quoted form of item 1 of argv & " " & quoted form of item 2 of argv
  end tell
end run
APPLESCRIPT
fi
exit 0
