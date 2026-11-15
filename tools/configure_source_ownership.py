#!/usr/bin/env python3
"""Archive source HALs superseded by stock M2381 blobs in this port.

Run after repo sync on the documented Android 16 tree. This does not edit the
manifest: another repo sync can restore these directories, so rerun the check.
"""
import argparse
from pathlib import Path

PATHS = (
    'hardware/qcom-caf/sm8550/audio',
    'vendor/qcom/opensource/audio-hal',
    'hardware/qcom-caf/sm8550/dataipa',
    'hardware/qcom-caf/sm8550/data-ipa-cfg-mgr',
    'hardware/qcom-caf/common/nqnfcinfo',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aosp', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--require-archived', action='store_true', help='Fail if any excluded source is present')
    args = parser.parse_args()
    aosp = args.aosp.resolve(strict=True)
    if not (aosp / 'build/envsetup.sh').is_file():
        parser.error('Not an Android source root')
    plan = []
    for relative in PATHS:
        source = aosp / relative
        backup = aosp / 'out/m2381-disabled-sources' / relative
        if source.is_symlink() or backup.is_symlink():
            raise ValueError(f'Refusing directory symlink: {relative}')
        if source.exists():
            if backup.exists():
                raise ValueError(f'Both source and backup exist: {relative}; review them manually')
            plan.append((source, backup))
    for source, backup in plan:
        print('archive:', source.relative_to(aosp))
        if args.apply:
            backup.parent.mkdir(parents=True, exist_ok=True)
            source.rename(backup)
    if args.require_archived and plan and not args.apply:
        raise ValueError('Source HALs superseded by vendor blobs are still present')
    print(f'{len(plan)} source directories {"archived" if args.apply else "would be archived"}; no device access')


if __name__ == '__main__':
    main()
