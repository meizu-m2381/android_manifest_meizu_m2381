#!/usr/bin/env python3
"""Run the device shared init-compatible split-policy compiler."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      'device/meizu/m2381/tools/compile_split_policy.py'),
                   run_name='__main__')
