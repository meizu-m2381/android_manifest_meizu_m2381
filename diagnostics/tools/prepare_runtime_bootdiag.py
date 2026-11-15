"""Resume Android init after a verified vendor-loader isolation experiment.

Keep C4 gating and the tested loader/blocklist. Use init's orderly reboot path
after three minutes without boot_completed; never use the raw restart2 timer
once userdata may be mounted. This only prepares host files.
"""
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-round', type=int, required=True)
    parser.add_argument('--round', type=int, required=True)
    parser.add_argument('--normal-init', type=Path, required=True)
    args = parser.parse_args()
    old, new = args.previous_round, args.round
    assert new > old >= 36
    args.output.mkdir(exist_ok=False)
    for path in args.previous.iterdir():
        if re.fullmatch(fr'(init|init.staged|watch|kmsg-wrapper|prepare-adb|checkpoint|modules.blocklist|vendor-modprobe)\.round{old}(\.rc|\.sh)?', path.name):
            data = path.read_bytes().replace(f'round{old}'.encode(), f'round{new}'.encode())
            data = data.replace(f'BOOTDIAG{old}'.encode(), f'BOOTDIAG{new}'.encode())
            (args.output / path.name.replace(f'round{old}', f'round{new}')).write_bytes(data)

    # Use the original unmodified late-init event order, including BPF and zygote.
    normal = args.normal_init.read_bytes()
    assert normal.count(b'    trigger late-fs\n') == 1
    assert normal.count(b'    trigger zygote-start\n') == 1
    (args.output / f'init.staged-round{new}.rc').write_bytes(normal)
    entry = args.output / f'init.round{new}.rc'
    text = entry.read_text(encoding='utf-8')
    text = text.replace('    start bootdiag_watch\n',
                        '    start bootdiag_watch\n    start bootdiag_deadline\n')
    text = text.replace(f'service bootdiag_deadline /metadata/bootdiag/bootdiag-deadline.round{new}',
                        f'service bootdiag_deadline /metadata/bootdiag/busybox sh /metadata/bootdiag/bootdiag-deadline.round{new}')
    text += '''
on post-fs-data
    start bootdiag_early_checkpoint

on property:ro.persistent_properties.ready=true
    start bootdiag_prepare_adb

on property:sys.boot_completed=1
    stop bootdiag_deadline
    write /dev/kmsg "<4>BOOTDIAG_RUNTIME: boot_completed=1"
'''
    entry.write_text(text, encoding='utf-8', newline='\n')

    deadline = '''#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
if [ "$1" = check ]; then $BB sleep 1; exit 0; fi
$BB sleep 180
if [ "$(/system/bin/getprop sys.boot_completed)" != 1 ]; then
    echo "<4>BOOTDIAG_RUNTIME: orderly_deadline_reboot" >/dev/kmsg
    /system/bin/setprop sys.powerctl reboot,bootloader
fi
'''
    (args.output / f'bootdiag-deadline.round{new}').write_text(deadline, encoding='utf-8', newline='\n')
    checkpoint = f'''#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
tick=0
while [ "$tick" -lt 180 ]; do
    data_mounted=0
    $BB grep -q ' /data ' /proc/mounts && data_mounted=1
    completed=$(/system/bin/getprop sys.boot_completed)
    echo "<4>BOOTDIAG{new}: runtime_tick=$tick data_mounted=$data_mounted boot_completed=$completed" >/dev/kmsg
    $BB sleep 1
    tick=$((tick + 1))
done
'''
    for name in ['watch', 'checkpoint']:
        (args.output / f'{name}.round{new}.sh').write_text(checkpoint, encoding='utf-8', newline='\n')
    adb = args.output / f'prepare-adb.round{new}.sh'
    adb_text = adb.read_bytes().replace(b'sys.bootdiag.phase paused', b'sys.bootdiag.phase running')
    marker = b'KEYS=/data/misc/adb/adb_keys\n'
    assert adb_text.count(marker) == 1
    # The wrapper's post-fs-data action runs before the imported normal init action.
    # Creating misc/adb there makes misc nonempty before encryption=Require is set.
    guard = b'''if [ "$(/system/bin/getprop ro.persistent_properties.ready)" != true ] || [ ! -d /data/misc ]; then
    echo data_directories_not_ready
    exit 1
fi
'''
    adb.write_bytes(adb_text.replace(marker, guard + marker))
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old, 'round': new,
        'change': 'restore normal late-init, retaining tested loader and tz_log blocklist',
        'userdata': 'normal Android mount and initialization; no wipe or format command added',
        'retained': 'C4 gating, original kernel and logical partitions, normal watchdog',
        'deadline': 'init orderly reboot to bootloader at 180s unless boot_completed=1',
        'limitation': 'requires working userspace for orderly reboot; C4 gating still diagnostic',
    }, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
