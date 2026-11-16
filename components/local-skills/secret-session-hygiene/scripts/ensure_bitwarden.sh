#!/usr/bin/env bash
# Report Bitwarden CLI readiness. Never print session tokens or secrets.
set -euo pipefail

if ! command -v bw >/dev/null 2>&1; then
  echo '{"ok":false,"error_class":"bw-missing"}'
  exit 1
fi

status_json="$(bw status 2>/dev/null || true)"
python3 - <<'PY' "$status_json"
import json, sys
raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print('{"ok":false,"error_class":"bw-status-unparsed"}')
    raise SystemExit(2)
status = data.get("status")
print(json.dumps({
    "ok": status in {"locked", "unlocked"},
    "status": status,
}))
if status == "unauthenticated":
    raise SystemExit(3)
PY
