"""Defer diagnostic ADB and preserve an exactly matched diagnostic-only misc directory."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-round', type=int, required=True)
    parser.add_argument('--round', type=int, required=True)
    args = parser.parse_args()
    old, new = args.previous_round, args.round
    assert (old, new) == (38, 39), 'This recovery is scoped to the first early-ADB experiments.'
    names = [f'init.round{old}.rc', f'init.staged-round{old}.rc',
             f'watch.round{old}.sh', f'kmsg-wrapper.round{old}.sh',
             f'prepare-adb.round{old}.sh', f'checkpoint.round{old}.sh',
             f'modules.blocklist.round{old}', f'vendor-modprobe.round{old}.sh',
             f'bootdiag-deadline.round{old}']
    contents = {name.replace(f'round{old}', f'round{new}'):
                (args.previous / name).read_bytes()
                .replace(f'round{old}'.encode(), f'round{new}'.encode())
                .replace(f'BOOTDIAG{old}'.encode(), f'BOOTDIAG{new}'.encode())
                for name in names}
    entry = f'init.round{new}.rc'
    text = contents[entry].decode('utf-8')
    original = 'on post-fs-data\n    start bootdiag_prepare_adb\n    start bootdiag_early_checkpoint\n'
    assert text.count(original) == 1
    text = text.replace(original, f'''on post-fs-data
    exec u:r:su:s0 root root -- /metadata/bootdiag/busybox sh /metadata/bootdiag/recover-adb-parent.round{new}.sh
    start bootdiag_early_checkpoint

on property:ro.persistent_properties.ready=true
    start bootdiag_prepare_adb
''')
    contents[entry] = text.encode('utf-8')
    adb = f'prepare-adb.round{new}.sh'
    marker = b'KEYS=/data/misc/adb/adb_keys\n'
    assert contents[adb].count(marker) == 1
    contents[adb] = contents[adb].replace(marker, b'''if [ "$(/system/bin/getprop ro.persistent_properties.ready)" != true ] || [ ! -d /data/misc ]; then
    echo data_directories_not_ready
    exit 1
fi
''' + marker)
    contents[f'recover-adb-parent.round{new}.sh'] = (
        Path(__file__).with_name('bootdiag_recover_adb_parent.sh').read_bytes()
        .replace(b'\r\n', b'\n'))
    args.output.mkdir(exist_ok=False)
    for name, data in contents.items():
        (args.output / name).write_bytes(data)
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old, 'round': new,
        'change': 'defer ADB until persistent properties; conditionally rename exact diagnostic contents',
        'preservation': 'no removal; unexpected files, original key backup, symlinks or mismatch leave misc untouched',
        'archive': '/data/misc.bootdiag-round39',
        'retained': 'complete Android init, images, tz_log blocklist, C4 isolation, orderly deadline',
        'first_stage': 'set printk_devkmsg=on before second-stage init opens its cached kmsg fd',
        'userdata': 'normal mount and policy application; no wipe, format or encryption bypass',
    }, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
