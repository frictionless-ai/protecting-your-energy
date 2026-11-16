#!/usr/bin/env python3
"""Run the bundled Independent Reconstruction command line."""

from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
runpy.run_path(str(Path(__file__).resolve().parents[1] / 'components/independent-reconstruction/scripts/ir.py'), run_name='__main__')
