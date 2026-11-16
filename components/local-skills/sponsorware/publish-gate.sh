#!/usr/bin/env bash
# Fail if source is recoverable from a repo that is about to be made public.
#
#   publish-gate.sh <repo-path> [--canary=STRING] <pathspec> [pathspec...]
#
# Pathspecs describe SOURCE, not the directory it used to live in. Match file
# types ('*.cpp' '*.hpp'), so a deliberate placeholder like src/SPONSORS-ONLY.md
# does not trip the gate.
#
# Example:
#   publish-gate.sh ./project-docs --canary=kJmpRel32Size '*.cpp' '*.hpp' '*.inc'
#
# Exit 0 = implemented local checks reported no selected source. Exit 1 = source recoverable, do not publish.

set -uo pipefail

REPO="${1:-}"
shift || true

CANARY=""
if [[ "${1:-}" == --canary=* ]]; then
    CANARY="${1#--canary=}"
    shift
fi

if [[ -z "$REPO" || $# -eq 0 ]]; then
    echo "usage: publish-gate.sh <repo-path> [--canary=STRING] <pathspec> [pathspec...]" >&2
    exit 2
fi

SPECS=("$@")

cd "$REPO" || { echo "cannot cd to $REPO" >&2; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "$REPO is not a git repo" >&2; exit 2; }

FAILED=0
pass() { printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAILED=1; }

echo "Pre-publish gate: $REPO"
echo "Source pathspecs: ${SPECS[*]}"
[[ -n "$CANARY" ]] && echo "Canary: $CANARY"
echo

# 1. Working tree / HEAD
n=$(git ls-files -- "${SPECS[@]}" | wc -l)
if [[ "$n" -eq 0 ]]; then
    pass "no tracked files match at HEAD"
else
    fail "$n tracked source files at HEAD"
    git ls-files -- "${SPECS[@]}" | sed 's/^/          /' | head -5
fi

# 2. Every commit on every ref -- the check that actually matters
n=$(git log --all --diff-filter=A --name-only --format='' -- "${SPECS[@]}" 2>/dev/null | grep -c . || true)
if [[ "$n" -eq 0 ]]; then
    pass "no commit on any ref ever added a source file"
else
    fail "$n source files were added somewhere in history (recoverable via 'git log -p')"
    git log --all --diff-filter=A --name-only --format='' -- "${SPECS[@]}" 2>/dev/null \
        | grep . | sort -u | sed 's/^/          /' | head -5
fi

# 3. Tags and branches pinning a source tree
bad_refs=""
while read -r ref; do
    [[ -z "$ref" ]] && continue
    if [[ -n "$(git ls-tree -r --name-only "$ref" -- "${SPECS[@]}" 2>/dev/null | head -1)" ]]; then
        bad_refs="$bad_refs $ref"
    fi
done < <(git for-each-ref --format='%(refname)' refs/tags refs/heads refs/remotes 2>/dev/null)

if [[ -z "$bad_refs" ]]; then
    pass "no tag or branch points at a tree containing source"
else
    fail "these refs contain source:$bad_refs"
fi

# 4. GitHub Releases ship auto-generated source tarballs
if command -v gh >/dev/null 2>&1; then
    rel=$(gh release list -L 5 2>/dev/null | grep -c . || true)
    if [[ "$rel" -eq 0 ]]; then
        pass "no GitHub Releases (no source tarballs)"
    else
        fail "$rel GitHub Release(s) exist -- each serves a source tarball of its tag"
    fi
else
    echo "  SKIP  gh not installed; check Releases manually"
fi

# 5. Dangling blobs -- survive a history rewrite until gc
dang=$(git fsck --unreachable --no-progress 2>/dev/null | grep -c '^unreachable blob' || true)
if [[ "$dang" -eq 0 ]]; then
    pass "no unreachable blobs in the object store"
else
    fail "$dang unreachable blobs present -- run: git reflog expire --expire=now --all && git gc --prune=now"
fi

# 6. Canary string anywhere in history
if [[ -n "$CANARY" ]]; then
    revs=$(git rev-list --all 2>/dev/null)
    if [[ -z "$revs" ]]; then
        pass "no commits to search for canary"
    else
        hits=$(git grep -I -l "$CANARY" $revs -- 2>/dev/null | wc -l)
        if [[ "$hits" -eq 0 ]]; then
            pass "canary '$CANARY' appears in no blob on any ref"
        else
            fail "canary '$CANARY' found in $hits blob(s) across history"
            git grep -I -l "$CANARY" $revs -- 2>/dev/null | sed 's/^/          /' | head -5
        fi
    fi
fi

echo
if [[ "$FAILED" -eq 0 ]]; then
    echo "LOCAL CHECKS PASSED -- review omitted and remote checks before publishing."
else
    echo "GATE FAILED -- source is recoverable. Do not make this repo public."
fi
exit "$FAILED"
