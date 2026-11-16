#!/usr/bin/env python3
"""Dispatch reconstruction commands from the installed package location."""

import os
import json
from pathlib import Path
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = PACKAGE_ROOT / 'components/thought-reconstruction/scripts/thought_reconstruct.py'
LIBRARY = PACKAGE_ROOT / 'components/thought-reconstruction-engine/bin/thought-reconstruction'
ADAPTER_COMMANDS = {'discover', 'acquire', 'inspect', 'assemble', '--version'}


def configure_identity():
    config_root = Path(os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')).expanduser()
    policy_path = Path(os.environ.get('PYE_ARCHIVE_POLICY_FILE') or str(config_root / 'protecting-your-energy/archive-policy.json')).expanduser()
    if not policy_path.exists():
        return
    if policy_path.stat().st_size > 1024 * 1024:
        raise ValueError('Archive policy exceeds the size limit')
    policy = json.loads(policy_path.read_text())
    if not isinstance(policy, dict):
        raise ValueError('Archive policy must be an object')
    owner = policy.get('owner_discord_id', '')
    aliases = policy.get('owner_aliases', [])
    archive_root = policy.get('archive_root', '')
    if not isinstance(archive_root, str):
        raise ValueError('Archive policy archive_root must be a string')
    if not isinstance(owner, str) or not isinstance(aliases, list) or any(not isinstance(item, str) for item in aliases):
        raise ValueError('Archive policy owner identity is malformed')
    if owner:
        os.environ.setdefault('THOUGHT_RECONSTRUCTION_OWNER_ID', owner)
    if aliases:
        os.environ.setdefault('THOUGHT_RECONSTRUCTION_OWNER_ALIASES', json.dumps(aliases))
    if archive_root:
        os.environ.setdefault('THOUGHT_RECONSTRUCTION_ARCHIVE', archive_root)
        os.environ.setdefault('PYE_ARCHIVE_ROOT', archive_root)


def main():
    arguments = sys.argv[1:]
    if not arguments or arguments[0] in ('--help', '-h'):
        print('Thought reconstruction\n\n'
              'Local acquisition and curated synthesis\n'
              '  discover, acquire, inspect, assemble\n\n'
              'Indexed library when configured or bundled\n'
              '  reclaim, rebuild, verify, query, task, merge-plan, flag-report\n\n'
              'Use <command> --help for command details. '
              'THOUGHT_RECONSTRUCTION_LEGACY_ENTRY selects an optional external library entrypoint. '
              'THOUGHT_RECONSTRUCTION_CONFIG selects its private configuration.')
        return 0
    adapter = arguments[0] in ADAPTER_COMMANDS
    configured = os.environ.get('THOUGHT_RECONSTRUCTION_LEGACY_ENTRY')
    entry = ADAPTER if adapter else (Path(configured).expanduser() if configured else LIBRARY)
    entry = entry.resolve(strict=False)
    if entry == Path(__file__).resolve() or not entry.is_file():
        message = 'The packaged acquisition adapter is unavailable.' if adapter else (
            'The optional indexed library is unavailable. Install its component or set '
            'THOUGHT_RECONSTRUCTION_LEGACY_ENTRY to the library entrypoint.')
        print(message, file=sys.stderr)
        return 1
    flags = ['-I'] if adapter else []
    if '--help' not in arguments and '-h' not in arguments:
        try:
            configure_identity()
        except (OSError, ValueError) as exc:
            print('Cannot load private archive identity configuration: ' + str(exc), file=sys.stderr)
            return 1
    os.execv(sys.executable, [sys.executable, *flags, str(entry), *arguments])


if __name__ == '__main__':
    raise SystemExit(main())
