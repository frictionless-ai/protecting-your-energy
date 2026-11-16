#!/usr/bin/env python3
"""Grade a compiled spec against the compile-spec skeleton.

Manual / opt-in: pipe live skill or prompt-engineer emit on stdin, or
pass a file. Does not spawn a host CLI. Exit 2 on shape fail.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from support.harness.shape_check import check_shape  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        help="compiled spec file; omit to read stdin",
    )
    args = parser.parse_args()
    if args.path:
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    result = check_shape(text)
    if result.ok:
        print("shape ok")
        return 0
    print("shape fail: " + "; ".join(result.reasons), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
