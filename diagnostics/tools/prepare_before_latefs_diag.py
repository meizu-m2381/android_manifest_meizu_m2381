"""Prepare a bounded before-late-fs diagnostic from the verified round18 inputs.

This creates host files only. It neither stages files on a device nor flashes it.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before, out = args.previous, args.output
    out.mkdir(parents=True, exist_ok=False)
    staged = (before / 'init.staged-round18.rc').read_text()
    start = staged.index('\non late-init\n')
    end = staged.index('\non early-fs\n', start)
    block = staged[start:end]
    assert block.count('    trigger late-fs\n') == 1
    block = block.replace('    trigger late-fs\n',
                          '    # Diagnostic: defer late-fs; keep userdata unmounted.\n')
    paused = block.index('on bootdiag-paused\n')
    resume = block.index('on property:sys.bootdiag.resume=1\n')
    block = block[:paused] + '''on bootdiag-paused
    write /dev/kmsg "<4>BOOTDIAG19: before_late_fs"
    start bootdiag_deadline
    start bootdiag_early_checkpoint

''' + block[resume:]
    # This timer uses a raw restart2 syscall and is valid only while data is unmounted.
    # Deliberately provide no resume trigger for this bounded diagnostic.
    block = block[:block.index('on property:sys.bootdiag.resume=1\n')]
    staged = staged[:start] + block + staged[end:]
    staged = staged.replace('round18', 'round19').replace('BOOTDIAG18', 'BOOTDIAG19')
    (out / 'init.staged-round19.rc').write_text(staged)

    entry = (before / 'init.round18.rc').read_text().replace('round18', 'round19')
    entry += '''
service bootdiag_deadline /metadata/bootdiag/bootdiag-deadline.round19
    disabled
    oneshot
    user root
    group root
    seclabel u:r:su:s0
    stdio_to_kmsg
'''
    (out / 'init.round19.rc').write_text(entry)
    for old, new in [('kmsg-wrapper.round18.sh', 'kmsg-wrapper.round19.sh'),
                     ('prepare-adb.round18.sh', 'prepare-adb.round19.sh'),
                     ('modules.blocklist.round18', 'modules.blocklist.round19')]:
        (out / new).write_text((before / old).read_text().replace('round18', 'round19'))
    # All observation subprocesses use static BusyBox. Avoid dynamic Android tools
    # until APEX setup; do not force writes to metadata through fsync or sync.
    (out / 'watch.round19.sh').write_text('''#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
exec >>/metadata/bootdiag/pixelos-round19-watch.txt 2>&1
echo watch_started
tick=0
while [ "$tick" -lt 35 ]; do
    echo "heartbeat=$tick"
    $BB cat /proc/uptime /proc/1/wchan
    echo
    $BB sleep 0.5
    tick=$((tick + 1))
done
''')
    (out / 'checkpoint.round19.sh').write_text('''#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
exec >>/metadata/bootdiag/pixelos-round19-checkpoint.txt 2>&1
echo checkpoint_before_late_fs
$BB cat /proc/uptime /proc/mounts
if $BB grep -q ' /data ' /proc/mounts; then
    echo UNEXPECTED_DATA_MOUNT
    exit 1
fi
tick=0
while [ "$tick" -lt 35 ]; do
    echo "checkpoint_tick=$tick"
    $BB cat /proc/uptime /proc/1/wchan
    echo
    echo "<4>BOOTDIAG19: checkpoint_tick=$tick" >/dev/kmsg
    $BB sleep 0.5
    tick=$((tick + 1))
done
echo checkpoint_survived_waiting_for_independent_deadline
''')
    (out / 'plan.json').write_text(json.dumps({
        'pause': 'before late-fs; no resume action',
        'kernel_and_logical_images': 'reuse round18 without changes',
        'deadline': 'static AArch64 nanosleep then restart2(bootloader), 20 seconds after pause',
        'limitation': 'cannot return if checkpoint not reached or kernel/reboot path stalls',
        'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [before / 'init.round18.rc', before / 'init.staged-round18.rc']},
    }, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
