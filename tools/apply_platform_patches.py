#!/usr/bin/env python3
"""Check or apply platform changes for the detected PixelOS major version."""
import argparse
import hashlib
import json
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def select_series(aosp, requested=None):
    if requested:
        return ROOT / requested
    version_file = aosp / 'vendor/custom/config/version.mk'
    if not version_file.is_file():
        raise ValueError('Cannot detect PixelOS version; choose --series explicitly for another ROM')
    version = re.search(r'^CUSTOM_PLATFORM_VERSION\s*:?=\s*(\d+)', version_file.read_text(), re.M)
    if not version or version[1] not in {'16', '17'}:
        raise ValueError('Unsupported PixelOS version')
    return ROOT / ('patches/platform-17-series.json' if version[1] == '17' else 'patches/platform-series.json')


def inspect(aosp, include_optional=False, series=None):
    plan = []
    for entry in json.loads((series or select_series(aosp)).read_text()):
        if entry['optional'] and not include_optional:
            continue
        path = aosp / entry['path']
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual == entry['after_sha256']:
            print('already applied:', entry['path'])
            continue
        if actual != entry['before_sha256']:
            raise ValueError(f"Unsupported source revision: {entry['path']}; review docs/patches.md")
        subprocess.run(['git', 'apply', '--check', str(ROOT / entry['patch'])],
                       cwd=aosp, check=True)
        plan.append(entry)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aosp', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Default is read-only validation')
    parser.add_argument('--include-r8-workaround', action='store_true')
    parser.add_argument('--require-applied', action='store_true', help='Fail if any required patch is pending')
    parser.add_argument('--series', help='Repository-relative series file; default detects PixelOS 16 or 17')
    args = parser.parse_args()
    aosp = args.aosp.resolve(strict=True)
    series = select_series(aosp, args.series)
    print('Platform series:', series.relative_to(ROOT))
    plan = inspect(aosp, args.include_r8_workaround, series)
    if args.require_applied and plan:
        raise ValueError('Required platform patches are still pending')
    if not args.apply:
        print(f'Validated {len(plan)} pending patches; no files changed')
        return
    # Precheck every input before changing any source. Keep originals outside scanned sources.
    for entry in plan:
        target = aosp / entry['path']
        original = target.read_bytes()
        if hashlib.sha256(original).hexdigest() != entry['before_sha256']:
            raise ValueError(f"Source changed during preflight: {target}")
        saved = aosp / 'out/m2381-source-backups' / entry['path']
        saved.parent.mkdir(parents=True, exist_ok=True)
        if saved.exists() and saved.read_bytes() != original:
            raise ValueError(f'Backup differs: {saved}')
        saved.write_bytes(original)
        subprocess.run(['git', 'apply', str(ROOT / entry['patch'])], cwd=aosp, check=True)
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry['after_sha256']:
            raise ValueError(f'Unexpected patch result: {target}; original saved at {saved}')
    print(f'Applied {len(plan)} patches')


if __name__ == '__main__':
    main()
