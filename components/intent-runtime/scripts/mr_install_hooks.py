#!/usr/bin/env python3
"""Install mission-runtime telemetry hooks into a non-Claude host.

Claude Code needs nothing from this script — it loads `hooks/hooks.json` from
the plugin directly and expands `${CLAUDE_PLUGIN_ROOT}` itself. Cursor, Copilot,
and Codex read hook configs from fixed locations outside the plugin and have no
equivalent placeholder, so their configs must be written out with an absolute
path to the recorder.

This writes to files the host owns, so it prints a plan and does nothing unless
you pass --apply. Existing files are backed up, never silently replaced.

    python3 scripts/mr_install_hooks.py --host cursor            # show plan
    python3 scripts/mr_install_hooks.py --host cursor --apply    # write it
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
RECORDER = os.path.join(HERE, "mr_record.py")

# Project scope is the default. User-wide installation is an explicit option.
TARGETS = {
    "cursor": {
        "template": "cursor.json",
        "user": "~/.cursor/hooks.json",
        "project": ".cursor/hooks.json",
        "note": "Cursor merges hook sources; project files need workspace trust.",
    },
    "copilot": {
        "template": "copilot.json",
        "user": "~/.copilot/hooks/mission-runtime.json",
        "project": ".github/hooks/mission-runtime.json",
        "note": "Copilot CLI reads ~/.copilot/hooks/*.json; VS Code reads "
                ".github/hooks/*.json and marks hooks as Preview.",
    },
    "codex": {
        "template": "codex.json",
        "user": "~/.codex/hooks.json",
        "project": ".codex/hooks.json",
        "note": "Codex requires one-time approval of command hooks via /hooks, "
                "and re-prompts whenever the command string changes.",
    },
}


def build_command() -> str:
    """The recorder invocation, quoted so an install path with spaces works."""
    return f'python3 "{RECORDER}"'


def resolve_target(host: str, scope: str, project: str) -> str:
    spec = TARGETS[host]
    if scope == "user":
        return os.path.abspath(os.path.expanduser(spec["user"]))
    return os.path.abspath(os.path.join(project, spec["project"]))


def render(host: str) -> str:
    path = os.path.join(PLUGIN_ROOT, "hooks", TARGETS[host]["template"])
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # The command is substituted inside a JSON string literal and itself
    # contains double quotes (to survive install paths with spaces), so it must
    # be JSON-escaped or the rendered file is not parseable.
    escaped = json.dumps(build_command())[1:-1]
    rendered = text.replace("__MR_CMD__", escaped)
    # Fail loudly here rather than writing a config the host will reject.
    json.loads(rendered)
    return rendered


def merge_config(existing: dict, incoming: dict) -> dict:
    """Merge event lists, retaining unrelated settings and existing commands."""
    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        raise ValueError("hook configuration must be a JSON object")
    result = dict(existing)
    for key, value in incoming.items():
        if key != "hooks":
            result.setdefault(key, value)
            continue
        hooks = dict(result.get("hooks", {}))
        if not isinstance(value, dict):
            raise ValueError("hooks must be an object")
        for event, commands in value.items():
            previous = hooks.get(event, [])
            if not isinstance(previous, list) or not isinstance(commands, list):
                raise ValueError(f"hook event {event} must be a list")
            merged = list(previous)
            seen = {json.dumps(item, sort_keys=True) for item in merged}
            for item in commands:
                identity = json.dumps(item, sort_keys=True)
                if identity not in seen:
                    merged.append(item)
                    seen.add(identity)
            hooks[event] = merged
        result[key] = hooks
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", required=True, choices=sorted(TARGETS))
    ap.add_argument("--scope", default="project", choices=("user", "project"))
    ap.add_argument("--project", default=os.getcwd(),
                    help="Project root for --scope project (default: cwd)")
    ap.add_argument("--apply", action="store_true",
                    help="Actually write. Without this, only the plan is shown.")
    args = ap.parse_args()

    if not os.path.isfile(RECORDER):
        print(f"error: recorder not found at {RECORDER}", file=sys.stderr)
        return 1

    target = resolve_target(args.host, args.scope, args.project)
    try:
        rendered = render(args.host)
        existing = {}
        if os.path.exists(target):
            with open(target, encoding="utf-8") as fh:
                existing = json.load(fh)
        rendered = json.dumps(merge_config(existing, json.loads(rendered)), indent=2) + "\n"
    except Exception as exc:
        print(f"error: could not render template: {exc}", file=sys.stderr)
        return 1

    print(f"host      {args.host}")
    print(f"scope     {args.scope}")
    print(f"recorder  {RECORDER}")
    print(f"target    {target}")
    print(f"note      {TARGETS[args.host]['note']}")
    exists = os.path.exists(target)
    if exists:
        print(f"merge     Existing settings retained in {target}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to write.")
        return 0

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if exists:
            stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
            backup = f"{target}.bak-{stamp}"
            shutil.copy2(target, backup)
            print(f"backed up {backup}")
        descriptor, temporary = tempfile.mkstemp(prefix=".intent-runtime-", dir=os.path.dirname(target))
        try:
            mode = os.stat(target).st_mode & 0o777 if exists else 0o600
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "w", encoding="utf-8") as fh:
                fh.write(rendered)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except Exception as exc:
        print(f"error: write failed: {exc}", file=sys.stderr)
        return 1

    print(f"wrote     {target}")
    print("Restart the host (or reload plugins) for hooks to take effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
