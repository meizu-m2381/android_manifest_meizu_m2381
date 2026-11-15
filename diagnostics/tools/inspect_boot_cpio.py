#!/usr/bin/env python3
"""Inspect newc ramdisks; extract only regular files under a separate directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat


def read_cpio(path):
    blob = path if isinstance(path, (bytes, bytearray)) else path.read_bytes()
    offset = 0
    while offset + 110 <= len(blob):
        if blob[offset:offset + 6] not in (b'070701', b'070702'):
            raise ValueError(f'Invalid newc header at {offset}')
        values = [int(blob[offset + 6 + i * 8:offset + 14 + i * 8], 16)
                  for i in range(13)]
        mode, size, namesize = values[1], values[6], values[11]
        start = offset + 110
        name = blob[start:start + namesize - 1].decode()
        start = (start + namesize + 3) & ~3
        end = start + size
        if end > len(blob):
            raise ValueError(f'Truncated entry: {name}')
        if name == 'TRAILER!!!':
            break
        yield name, mode, blob[start:end]
        offset = (end + 3) & ~3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cpio', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, mode, data in read_cpio(args.cpio):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError(f'Unsafe entry: {name}')
        item = {'name': name, 'mode': oct(mode), 'size': len(data)}
        if stat.S_ISREG(mode):
            target = args.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            # Never create archive symlinks; do not follow any preexisting links.
            if not target.resolve().is_relative_to(args.output.resolve()):
                raise ValueError(f'Unsafe target: {target}')
            target.write_bytes(data)
            item['sha256'] = hashlib.sha256(data).hexdigest()
        elif stat.S_ISLNK(mode):
            item['link'] = data.decode(errors='replace')
        manifest.append(item)
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'entries': len(manifest),
                      'modules': sum(x['name'].endswith('.ko') for x in manifest),
                      'output': str(args.output)}))


if __name__ == '__main__':
    main()
