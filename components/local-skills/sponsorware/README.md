# sponsorware

A Claude Code skill for putting a codebase behind a paid sponsor wall without
leaking the source.

The hard part is not hiding the code. It is proving the code is actually gone
before you make a repo public. Deleting `src/` in a new commit protects nothing,
because `git log -p` recovers every earlier version. This skill covers the split,
the licensing, and a gate that checks history rather than the working tree.

## Install

```sh
git clone https://github.com/bodencrouch/sponsorware-skill ~/.agents/skills/sponsorware
ln -s ~/.agents/skills/sponsorware ~/.claude/skills/sponsorware
```

Claude Code picks it up on the next session. Ask it to make a repo
sponsors-only, or invoke `/sponsorware`.

## Use the gate on its own

The gate is a plain shell script. It needs no agent.

```sh
./publish-gate.sh <repo-path> [--canary=STRING] <pathspec>...
```

Describe source by file type, not by directory, so a deliberate placeholder like
`src/SPONSORS-ONLY.md` does not trip it:

```sh
./publish-gate.sh ./myproject-docs --canary=kJmpRel32Size '*.cpp' '*.hpp' '*.inc'
```

Exit 0 means the helper reported no selected source in its completed checks. Resolve skipped checks, command failures and external artifacts separately before publication. Exit 1 records a detected issue.

## What the gate checks

It reads every ref, not just `HEAD`:

| Check | Why |
|---|---|
| Tracked files at `HEAD` | The obvious one |
| Any commit that ever *added* source | `git log -p` recovers it |
| Tags and branches pointing at a source tree | A tag pins a whole tree off `main` |
| GitHub Releases | Each serves a source tarball of its tag |
| Unreachable blobs | Survive a history rewrite until `git gc` |
| A canary string across all blobs | Catches source you forgot to name |

One vector it cannot fix: **merged pull request diffs stay readable on a public
repo even after a history rewrite.** If a PR ever carried the source, rewriting
history does not close it. That is the main reason the skill recommends a fresh
public repo over purging an existing one.

## Files

- `SKILL.md` — the procedure: split, licensing, GitHub Sponsors wiring
- `publish-gate.sh` — the pre-publish check

## Licence

MIT.
