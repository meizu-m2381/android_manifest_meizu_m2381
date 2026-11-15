"""Preserve framework failure evidence without changing the tested boot flow."""
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
    assert new > old >= 42
    names = [f'init.round{old}.rc', f'init.staged-round{old}.rc',
             f'watch.round{old}.sh', f'kmsg-wrapper.round{old}.sh',
             f'prepare-adb.round{old}.sh', f'checkpoint.round{old}.sh',
             f'modules.blocklist.round{old}', f'vendor-modprobe.round{old}.sh',
             f'bootdiag-deadline.round{old}', f'recover-adb-parent.round{old}.sh']
    contents = {name.replace(f'round{old}', f'round{new}'):
                (args.previous / name).read_bytes()
                .replace(f'round{old}'.encode(), f'round{new}'.encode())
                .replace(f'BOOTDIAG{old}'.encode(), f'BOOTDIAG{new}'.encode())
                for name in names}
    entry = f'init.round{new}.rc'
    before = contents[entry]
    assert before.count(b'-b main -b system -b crash') == 1
    assert before.count(b'auditd:S logd:S kmsg:S *:V') == 1
    contents[entry] = (before.replace(b'-b main -b system -b crash',
                                     b'-b main -b system -b crash -b events')
                       .replace(b'auditd:S logd:S kmsg:S *:V',
                                b'auditd:S logd:S kmsg:S audioadsprpcd:S DMABUFHEAPS:W *:V'))
    # Keep a small independent record after the capped early kmsg file fills.
    contents[f'watch.round{new}.sh'] = f'''#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
OUT=/metadata/bootdiag/pixelos-round{new}-runtime.txt
[ -L "$OUT" ] && exit 2
exec >>"$OUT" 2>&1
echo runtime_start
$BB cat /proc/sys/kernel/random/boot_id
tick=0
while [ "$tick" -lt 180 ]; do
    echo "runtime_tick=$tick"
    $BB cat /proc/uptime
    echo "boot_completed=$(/system/bin/getprop sys.boot_completed)"
    echo "zygote=$(/system/bin/getprop init.svc.zygote)"
    echo "surfaceflinger=$(/system/bin/getprop init.svc.surfaceflinger)"
    echo "adbd=$(/system/bin/getprop init.svc.adbd)"
    echo "usb=$(/system/bin/getprop sys.usb.state)"
    echo "system_server_pid=$(/system/bin/pidof system_server)"
    echo "surfaceflinger_pid=$(/system/bin/pidof surfaceflinger)"
    $BB sync
    $BB sleep 5
    tick=$((tick + 5))
done
'''.encode()
    args.output.mkdir(exist_ok=False)
    for name, data in contents.items():
        (args.output / name).write_bytes(data)
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old, 'round': new,
        'change': 'filter repetitive audio RPC logs, include events, persist runtime snapshots',
        'evidence': 'round42 final rotated logs cover only 7.5 seconds of audio RPC retries',
        'retained': 'Vulkan mapper fix, all logical images, normal init, encryption and 180s deadline',
        'userdata': 'no wipe, format, mount or encryption change',
    }, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
