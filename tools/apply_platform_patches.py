#!/usr/bin/env python3
"""Check/restore retired Android 17 platform changes; retain Android 16 history."""
import argparse
import hashlib
import json
import subprocess
import re
import tempfile
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


def inspect_unpatched(aosp, series):
    """Preflight the entire retired series; unknown source versions stay untouched."""
    plan = []
    for entry in json.loads(series.read_text()):
        if entry['optional']:
            continue
        actual = hashlib.sha256((aosp / entry['path']).read_bytes()).hexdigest()
        if actual == entry['before_sha256']:
            continue
        if actual != entry['after_sha256']:
            raise ValueError(f"Unsupported source revision: {entry['path']}; no files changed")
        plan.append(entry)
    return plan


def restore(aosp, plan):
    # Reverse and verify every patch off-tree before changing a single source file.
    outputs = []
    with tempfile.TemporaryDirectory(prefix='m2381-platform-restore-') as temporary:
        stage = Path(temporary)
        for entry in plan:
            target = aosp / entry['path']
            original = target.read_bytes()
            if hashlib.sha256(original).hexdigest() != entry['after_sha256']:
                raise ValueError(f'Source changed during preflight: {target}')
            staged = stage / entry['path']
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(original)
            subprocess.run(['git', 'apply', '--reverse', str(ROOT / entry['patch'])],
                           cwd=stage, check=True)
            data = staged.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry['before_sha256']:
                raise ValueError(f'Unexpected restored content: {target}')
            outputs.append((target, original, data))
    for target, original, data in outputs:
        if target.read_bytes() != original:
            raise ValueError(f'Source changed during restore: {target}')
    for target, _, data in outputs:
        # Atomic replacement also avoids writing through historical hard links.
        temporary = target.with_name(target.name + '.m2381-restore.tmp')
        try:
            temporary.write_bytes(data)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aosp', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Default is read-only validation')
    parser.add_argument('--include-r8-workaround', action='store_true')
    parser.add_argument('--require-applied', action='store_true', help='Fail if any required patch is pending')
    parser.add_argument('--require-unpatched', action='store_true', help='Require the recorded upstream files, with no M2381 platform patches')
    parser.add_argument('--restore', action='store_true', help='Reverse only known platform patches, refusing unknown changes')
    parser.add_argument('--series', help='Repository-relative series file; default detects PixelOS 16 or 17')
    args = parser.parse_args()
    aosp = args.aosp.resolve(strict=True)
    series = select_series(aosp, args.series)
    print('Platform series:', series.relative_to(ROOT))
    if args.restore or args.require_unpatched:
        if args.apply or args.require_applied or (args.restore and args.require_unpatched):
            parser.error('Choose one platform migration/check mode')
        plan = inspect_unpatched(aosp, series)
        if args.require_unpatched and plan:
            raise ValueError('Retired platform patches remain; commit local changes, then use --restore')
        if args.restore:
            restore(aosp, plan)
        print(f'Platform isolation: {len(plan)} restored; upstream source verified')
        return
    if series.name == 'platform-17-series.json' and (args.apply or args.require_applied):
        parser.error('Android 17 platform patches are retired; use device blob compatibility and --require-unpatched')
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
