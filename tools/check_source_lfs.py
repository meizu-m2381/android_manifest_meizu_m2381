#!/usr/bin/env python3
"""Reject unmaterialized PixelOS prebuilt LFS pointers before building images."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    prebuilts = root / 'vendor/pixel'
    if not prebuilts.is_dir():
        raise ValueError('Missing vendor/pixel prebuilt directory')
    missing = []
    for directory, dirs, files in os.walk(prebuilts, followlinks=False):
        dirs[:] = [d for d in dirs if d != '.git']
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024:
                continue
            if path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1\n'):
                missing.append(str(path.relative_to(root)))
    if missing:
        raise ValueError('Download current-revision Git LFS payloads before building:\n' + '\n'.join(sorted(missing)))
    print('PixelOS prebuilt LFS pointer check passed')


if __name__ == '__main__':
    main()
