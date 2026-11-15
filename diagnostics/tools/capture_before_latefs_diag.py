"""Archive diagnostic device logs with matching device and host SHA256 digests."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--round', type=int, default=19)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = root / f'logs/boot-audit-20261112/round{args.round}/capture'
    out.mkdir(parents=True, exist_ok=False)

    def adb(*command):
        return subprocess.run([args.adb, '-s', args.serial, *command],
                              check=True, capture_output=True, timeout=60).stdout

    assert adb('get-state').strip() == b'recovery'
    assert b' /metadata ' in adb('shell', 'cat', '/proc/mounts')
    assert b' /data ' not in adb('shell', 'cat', '/proc/mounts')
    remote = '/metadata/bootdiag/'
    files = adb('shell', 'find', '/metadata/bootdiag', '-maxdepth', '1',
                '-type', 'f', '-name', f'pixelos-round{args.round}-*').decode().splitlines()
    assert files, 'No diagnostic files: do not infer successful candidate boot.'
    pstore = adb('shell', 'find', '/sys/fs/pstore', '-maxdepth', '1', '-type', 'f')
    files += pstore.decode().splitlines()
    records = []
    for name in sorted(files):
        assert name.startswith((remote + f'pixelos-round{args.round}-', '/sys/fs/pstore/'))
        path = out / Path(name).name
        sha = adb('shell', 'sha256sum', name).decode().split()[0]
        adb('pull', name, str(path))
        with path.open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == sha
        assert adb('shell', 'sha256sum', name).decode().split()[0] == sha
        records.append(dict(remote=name, local=path.relative_to(root).as_posix(),
                            bytes=path.stat().st_size, sha256=sha))
    (out / 'verified-files.json').write_text(json.dumps(records, indent=2) + '\n')
    print(f'{len(records)} device files archived and verified; no device files removed.')


if __name__ == '__main__':
    main()
