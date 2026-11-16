#!/usr/bin/env python3
"""Compose the bundled context and archive hooks into one host response."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_hook(command, payload):
    result = subprocess.run(command, input=json.dumps(payload), text=True,
                            capture_output=True, timeout=5, cwd=ROOT)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'hook exited with an error')
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', choices=('claude', 'codex', 'auto'), default='auto')
    args = parser.parse_args()
    host = args.host
    if host == 'auto':
        host = 'claude' if os.environ.get('CLAUDE_PLUGIN_ROOT') else 'codex'
    try:
        payload = json.load(sys.stdin)
    except (ValueError, UnicodeError):
        print('{}')
        return
    if not isinstance(payload, dict):
        print('{}')
        return
    output = {}
    notices = []
    guard = ROOT / 'integrations/shared/archive_guard.py'
    try:
        if guard.is_file():
            output = json.loads(run_hook([sys.executable, str(guard), '--host', host], payload) or '{}')
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        notices.append('Archive hook could not run: ' + str(exc))
    event = payload.get('hook_event_name')
    if event == 'PermissionDenied':
        try:
            run_hook([sys.executable, str(ROOT / 'components/token-guide/hooks/guide.py')], payload)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            notices.append('Advisory hook could not run: ' + str(exc))
    if event in ('UserPromptSubmit', 'PostToolUse', 'PostToolUseFailure'):
        context = []
        prior = output.get('hookSpecificOutput', {}).get('additionalContext')
        if prior:
            context.append(prior)
        commands = [([sys.executable, str(ROOT / 'components/token-guide/hooks/guide.py')], True)]
        if event == 'UserPromptSubmit':
            commands.extend([
                (['sh', str(ROOT / 'integrations/shared/turn-digest.sh')], False),
                ([sys.executable, str(ROOT / 'components/semantic-expression/hooks/intent_coach.py')], True),
            ])
        for command, structured in commands:
            try:
                value = run_hook(command, payload)
                if structured:
                    value = json.loads(value or '{}').get('hookSpecificOutput', {}).get('additionalContext', '')
                if value.strip():
                    context.append(value.strip())
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                notices.append('Context hook could not run: ' + str(exc))
        context.extend(notices)
        if context:
            specific = output.setdefault('hookSpecificOutput', {})
            specific['hookEventName'] = event
            specific['additionalContext'] = '\n\n'.join(context)
    elif notices:
        print('\n'.join(notices), file=sys.stderr)
    print(json.dumps(output))


if __name__ == '__main__':
    main()
