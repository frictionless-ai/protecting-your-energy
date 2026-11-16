#!/usr/bin/env python3
"""Run the package's prompt-submit guidance hook."""

from pathlib import Path
import runpy


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / 'components/semantic-expression/hooks/intent_coach.py'),
                   run_name='__main__')
