#!/bin/sh
# turn-digest: per-turn digest for prompt-submit hooks (Claude Code, Codex, Cursor, Gemini, OpenCode).
#
#   turn-digest.sh                 print the digest as plain text (Claude Code UserPromptSubmit, Codex UserPromptSubmit)
#   turn-digest.sh json gemini     wrap it for Gemini BeforeAgent:  {"hookSpecificOutput":{"hookEventName":"BeforeAgent","additionalContext":...}}
#   turn-digest.sh json cursor     wrap it for Cursor sessionStart: {"additional_context":...}
#   turn-digest.sh path [dir]      print the ledger path for dir (default $PWD)
#   turn-digest.sh add "text"      append one directive line to the ledger for $PWD
#
# All digest modes read the hook's JSON on stdin when present and take the project directory from
# .cwd (Claude Code, Codex, Gemini) or .workspace_roots[0] (Cursor); OpenCode's plugin passes {"cwd":...}.
# The ledger is a markdown checklist at $AGENT_LEDGER_ROOT/<cwd-slug>/directives.md
# (default root ~/.cache/agent-runs/ledger). It persists across sessions on purpose.
#
# Gemini runs hooks in a sanitized environment, so HOME and PATH get fallbacks here.
set -u
PATH=${PATH:-/usr/bin:/bin}:/usr/local/bin:/usr/bin:/bin
runtime_home=${HOME:-$(getent passwd "$(id -u)" 2>/dev/null | cut -d: -f6)}
export PATH
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
digest_script=${PYE_TURN_DIGEST_SCRIPT:-$script_dir/turn-digest.sh}

root=${AGENT_LEDGER_ROOT:-$runtime_home/.cache/agent-runs/ledger}
max_lines=${TURN_DIGEST_MAX_LINES:-40}

slug_of() {
  printf '%s' "$1" | sed 's#^/##; s#[/ ]#-#g'
}

ledger_for() {
  printf '%s/%s/directives.md' "$root" "$(slug_of "$1")"
}

cwd_from_stdin() {
  [ -t 0 ] && return 0
  input=$(cat 2>/dev/null || true)
  [ -n "$input" ] || return 0
  command -v jq >/dev/null 2>&1 || return 0
  printf '%s' "$input" | jq -r '.cwd // (.workspace_roots[0]? // empty) // .workspace_root // .workspace // empty' 2>/dev/null
}

print_digest() {
  ledger=$(ledger_for "$1")
  echo "Coverage/continuity: address every request, question, correction and constraint; follow-ups steer the existing task and do not erase earlier directives; after answering or correcting, continue active authorized work. A finished step or status report is not task completion. Use existing authoritative project destinations. At phase transitions apply the most relevant installed expert workflow, then continue the next useful authorized action. Investigate and finish coherent dirty Git work under the active publication permissions. After context recovery, ground conceptual descriptions in useful established terms and continue execution."
  echo "== turn digest $(date +%H:%M) =="
  echo "Behaviours: recover missing context (conversation, named material, notes, archive) before interpreting; never fill a gap with an assumption, state only what recovery could not settle; stop and name confusion instead of guessing; push back with a concrete downside; prefer the simplest version that works; touch only what the task needs; done means verified with evidence."
  echo "Drive: after a finished step take the next in-scope step without waiting while authorized work remains."
  echo "Phase: select a relevant installed skill when the phase changes; keep context loading proportional to the task and preserve the requested completion scope."
  if [ -s "$ledger" ]; then
    echo "Directives ledger ($ledger), open items first:"
    grep -v '^[[:space:]]*$' "$ledger" | grep -- '- \[ \]' | tail -n "$max_lines"
    done_n=$(grep -c -- '- \[x\]' "$ledger" 2>/dev/null)
    [ "${done_n:-0}" -gt 0 ] && echo "($done_n done items not shown)"
  else
    echo "Directives ledger: empty. Append each user directive or todo with: $digest_script add \"<text>\"  (file: $ledger). Tick an item with [x] when verified done."
  fi
  echo "== end digest =="
}

case "${1:-}" in
  path)
    ledger_for "${2:-$PWD}"
    echo
    exit 0
    ;;
  add)
    shift
    [ $# -gt 0 ] || { echo "usage: turn-digest.sh add \"text\"" >&2; exit 2; }
    ledger=$(ledger_for "$PWD")
    mkdir -p "$(dirname "$ledger")"
    printf -- '- [ ] %s %s\n' "$(date +%Y-%m-%d)" "$*" >> "$ledger"
    echo "added to $ledger"
    exit 0
    ;;
  json)
    format=${2:-}
    case "$format" in gemini|cursor) ;; *) echo "usage: turn-digest.sh json gemini|cursor" >&2; exit 2 ;; esac
    cwd=$(cwd_from_stdin); [ -n "$cwd" ] || cwd=$PWD
    digest=$(print_digest "$cwd")
    if ! command -v jq >/dev/null 2>&1; then
      # Without jq we cannot escape safely; emit an empty object so the host still proceeds.
      echo '{}'; exit 0
    fi
    case "$format" in
      gemini) printf '%s' "$digest" | jq -Rsc '{hookSpecificOutput: {hookEventName: "BeforeAgent", additionalContext: .}}' ;;
      cursor) printf '%s' "$digest" | jq -Rsc '{additional_context: .}' ;;
    esac
    exit 0
    ;;
  "") ;;
  *) echo "usage: turn-digest.sh [path [dir] | add \"text\" | json gemini|cursor]" >&2; exit 2 ;;
esac

cwd=$(cwd_from_stdin); [ -n "$cwd" ] || cwd=$PWD
print_digest "$cwd"
