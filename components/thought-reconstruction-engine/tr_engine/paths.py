"""Repo-root discovery and source configuration."""
import glob
import os

WORK_DIR_NAME = "thought-reconstruction-work"

# Default sources, repo-root relative. Archive partitions are opt-in via
# --source, never default (huge, slow media).
DEFAULT_SOURCES = [
    "y2/THOUGHT-STREAM.md",
    "y2/adamant.json",
    "docs/essays/_sources/*.jsonl",
    "inbox/",
]


def find_repo_root(explicit=None):
    """Resolve the repo root.

    Use --repo-root or THOUGHT_RECONSTRUCTION_REPO_ROOT when configured.
    Otherwise walk upward from the working directory looking for y2/.
    """
    explicit = explicit or os.environ.get('THOUGHT_RECONSTRUCTION_REPO_ROOT')
    if explicit:
        root = os.path.abspath(explicit)
        if not os.path.isdir(root):
            raise SystemExit("repo root does not exist: %s" % root)
        return root
    here = os.getcwd()
    cur = here
    while True:
        if os.path.isdir(os.path.join(cur, "y2")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise SystemExit(
                "could not find repo root (no y2/ in any parent of %s); "
                "pass --repo-root" % here
            )
        cur = parent


def work_dir(repo_root):
    return os.path.join(repo_root, WORK_DIR_NAME)


def resolve_sources(repo_root, extra=None):
    """Expand the default source list (plus any --source extras) to
    (label, absolute-path) pairs. Labels are repo-root relative when the
    path is under the root. Missing defaults are skipped silently."""
    patterns = list(DEFAULT_SOURCES) + list(extra or [])
    out = []
    seen = set()
    for pat in patterns:
        abspat = pat if os.path.isabs(pat) else os.path.join(repo_root, pat)
        matches = sorted(glob.glob(abspat)) if any(c in pat for c in "*?[") else [abspat]
        for m in matches:
            m = m.rstrip(os.sep)
            if not os.path.exists(m) or m in seen:
                continue
            seen.add(m)
            label = os.path.relpath(m, repo_root)
            if label.startswith(".."):
                label = m
            out.append((label, m))
    return out
