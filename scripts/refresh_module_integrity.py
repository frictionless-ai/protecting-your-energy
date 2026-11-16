#!/usr/bin/env python3
"""Refresh package module pins after reviewing a source change."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='write the reviewed package hashes')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    paths = list((root / 'scripts').glob('*.py'))
    paths.extend((root / 'components/archive-retrieval').glob('*.py'))
    expected = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(paths)}
    destination = root / 'assets/module-integrity.json'
    current = json.loads(destination.read_text()) if destination.exists() else {}
    if current == expected:
        print('Package module hashes are current.')
        return 0
    if not args.write:
        print('Package module hashes differ. Review the source changes, then use --write.')
        return 1
    descriptor, temporary = tempfile.mkstemp(prefix='.module-integrity-', dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'w') as handle:
            json.dump(expected, handle, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Updated package module hashes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
