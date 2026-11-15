#!/usr/bin/env python3
"""Verify the bundled firmware inputs and retained pre-fixup originals."""
import argparse
import json
from pathlib import Path
from check_local_inputs import ROOT, check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    entries = json.loads((ROOT / 'provenance/bundled-inputs.json').read_text(encoding='utf-8'))['files']
    errors = check(args.root, entries)
    for path, reason in errors[:30]:
        print(reason, path)
    print(f'Bundled inputs: {len(entries)} checked, {len(errors)} errors')
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
