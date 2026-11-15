"""Stage verified before-late-fs diagnostics in recovery, without flashing."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--round', type=int, default=19)
    parser.add_argument('--prune-archived-round', type=int,
                        help='Remove only logs matching a verified local archive')
    parser.add_argument('--updated-vendor-image', action='store_true',
                        help='Allow a separately verified vendor image change (requires fastbootd flash)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    number = args.round
    if number < 19:
        raise ValueError('only before-late-fs diagnostics from round19 are supported')
    here = root / f'logs/boot-audit-20261112/round{number}'
    images = root / f'flash_images/selinux-fix-20261112/logging-round{number}'
    remote = '/metadata/bootdiag/'

    def adb(*command):
        return subprocess.run([args.adb, '-s', args.serial, *command],
                              capture_output=True, check=True, timeout=30).stdout

    assert adb('get-state').strip() == b'recovery'
    mounts = adb('shell', 'cat', '/proc/mounts').decode()
    assert ' /metadata ' in mounts and ' /data ' not in mounts
    minimum_free_kib = 8192 if number >= 37 else 2048
    assert int(adb('shell', remote + 'busybox', 'df', '-Pk', '/metadata')
               .decode().splitlines()[-1].split()[3]) > minimum_free_kib
    manifest = {x['name']: x for x in json.loads((images / 'manifest.json').read_text())}
    old_images = root / f'flash_images/selinux-fix-20261112/logging-round{number - 1}'
    old = {x['name']: x for x in json.loads((old_images / 'manifest.json').read_text())}
    assert old.keys() == manifest.keys()
    expected_changes = ['vbmeta.img', 'vendor_boot.img']
    if args.updated_vendor_image:
        expected_changes.append('vendor.img')
    assert sorted(n for n in old if old[n] != manifest[n]) == sorted(expected_changes)
    image_names = ['boot.img', 'init_boot.img', 'vendor_boot.img', 'vbmeta_system.img', 'vbmeta.img']
    if args.updated_vendor_image:
        image_names.append('vendor.img')
    for name in image_names:
        path = images / name
        assert path.stat().st_size == manifest[name]['size']
        assert digest(path) == manifest[name]['sha256']
    removed = []
    if args.prune_archived_round is not None:
        old_number = args.prune_archived_round
        assert 19 <= old_number < number
        archive = root / f'logs/boot-audit-20261112/round{old_number}/capture/verified-files.json'
        for item in json.loads(archive.read_text()):
            name = item['remote']
            if not name.startswith(remote + f'pixelos-round{old_number}-'):
                continue
            local = root / item['local']
            assert local.stat().st_size == item['bytes'] and digest(local) == item['sha256']
            assert adb('shell', 'sha256sum', name).decode().split()[0] == item['sha256']
            removed.append(name)
        assert removed
        adb('shell', 'rm', '-f', *removed)
    records = []
    names = [f'init.round{number}.rc', f'init.staged-round{number}.rc', f'watch.round{number}.sh',
             f'kmsg-wrapper.round{number}.sh', f'prepare-adb.round{number}.sh',
             f'modules.blocklist.round{number}', f'checkpoint.round{number}.sh',
             f'bootdiag-deadline.round{number}']
    loader_script = f'vendor-modprobe.round{number}.sh'
    if (here / loader_script).exists():
        names.append(loader_script)
    recovery_script = f'recover-adb-parent.round{number}.sh'
    if (here / recovery_script).exists():
        names.append(recovery_script)
    shell_count = 0
    for name in names:
        path = here / name
        adb('push', str(path), remote + name)
        executable = name.startswith('bootdiag-deadline.') or name == loader_script
        adb('shell', 'chmod', '700' if executable else '644', remote + name)
        sha = digest(path)
        assert adb('shell', 'sha256sum', remote + name).decode().split()[0] == sha
        if name.endswith('.sh'):
            adb('shell', remote + 'busybox', 'sh', '-n', remote + name)
            shell_count += 1
        records.append(dict(name=name, bytes=path.stat().st_size, sha256=sha))
    started = time.monotonic()
    adb('shell', remote + f'bootdiag-deadline.round{number}', 'check')
    duration = time.monotonic() - started
    assert duration >= 0.9, duration
    (here / 'staged-files.json').write_text(json.dumps({
        'files': records, 'deadline_check_seconds': duration,
        'userdata_unmounted': True, 'removed_verified_logs': removed,
        'required_fastbootd_images': ['vendor.img'] if args.updated_vendor_image else [],
    }, indent=2) + '\n')
    before = adb('exec-out', 'dd if=/dev/block/by-name/misc bs=2048 count=1 2>/dev/null')
    assert len(before) == 2048
    # bootloader/recovery writes need not erase bytes beyond the first NUL.
    assert before[:32].split(b'\0', 1)[0] in (b'', b'boot-recovery'), repr(before[:32])
    (here / 'bcb-before.bin').write_bytes(before)
    adb('shell', 'dd', 'if=/dev/zero', 'of=/dev/block/by-name/misc',
        'bs=1', 'count=32', 'conv=notrunc')
    adb('shell', 'sync')
    after = adb('exec-out', 'dd if=/dev/block/by-name/misc bs=2048 count=1 2>/dev/null')
    assert len(after) == 2048 and after[:32] == bytes(32) and after[32:] == before[32:]
    (here / 'bcb-after.bin').write_bytes(after)
    print(f'{len(image_names)} images and {len(records)} staged files verified; {shell_count} shell syntax checks passed.')
    print(f'Static deadline check passed; BCB bytes 32-2047 unchanged; {len(removed)} archived logs removed.')


if __name__ == '__main__':
    main()
