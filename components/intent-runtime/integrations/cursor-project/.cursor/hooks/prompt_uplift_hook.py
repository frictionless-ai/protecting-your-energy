#!/usr/bin/env python3
"""Delegate an optional project hook to the installed canonical component."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import sys


def main() -> None:
    configured = os.environ.get("INTENT_RUNTIME_ROOT")
    roots = [Path(configured).expanduser()] if configured else Path(__file__).resolve().parents
    for root in roots:
        canonical = root / "hooks" / "prompt_uplift_hook.py"
        if canonical.is_file() and canonical.resolve() != Path(__file__).resolve():
            sys.path.insert(0, str(root))
            runpy.run_path(str(canonical), run_name="__main__")
            return
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
