"""Prepare round23 by bypassing only vendor.modprobe's bulk driver loader."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    names = ['init.round22.rc', 'init.staged-round22.rc', 'watch.round22.sh',
             'kmsg-wrapper.round22.sh', 'prepare-adb.round22.sh',
             'modules.blocklist.round22', 'checkpoint.round22.sh']
    for name in names:
        content = (args.previous / name).read_text()
        content = content.replace('round22', 'round23').replace('BOOTDIAG22', 'BOOTDIAG23')
        if name == 'init.round22.rc':
            anchor = 'on early-init\n'
            assert content.count(anchor) == 2
            content = content.replace(anchor, anchor +
                '    mount none /metadata/bootdiag/vendor-modprobe.round23.sh '
                '/vendor/bin/vendor_modprobe.sh bind\n', 1)
        if name == 'checkpoint.round22.sh':
            anchor = 'checkpoint_before_late_fs\n'
            assert content.count(anchor) == 1
            content = content.replace(anchor, anchor + '''$BB cat /proc/modules
for module in msm_drm msm_kgsl camera kiwi_v2; do
    if $BB grep -q "^$module " /proc/modules; then loaded=1; else loaded=0; fi
    echo "<4>BOOTDIAG23: $module loaded=$loaded" >/dev/kmsg
done
''')
        (args.output / name.replace('round22', 'round23')).write_text(content)
    # The original service runs as root using /vendor/bin/sh. Preserve its
    # completion property so post-fs can reach the same diagnostic checkpoint.
    (args.output / 'vendor-modprobe.round23.sh').write_text('''#!/vendor/bin/sh
echo "<4>BOOTDIAG23: vendor_modprobe_bulk_load_bypassed" >/dev/kmsg
if ! /vendor/bin/setprop vendor.all.modules.ready 1; then
    echo "<3>BOOTDIAG23: diagnostic_readiness_failed" >/dev/kmsg
    exit 1
fi
echo "<4>BOOTDIAG23: diagnostic_readiness_signalled" >/dev/kmsg
exit 0
''')
    deadline = args.previous / 'bootdiag-deadline.round22'
    shutil.copyfile(deadline, args.output / 'bootdiag-deadline.round23')
    (args.output / 'plan.json').write_text(json.dumps({
        'pause': 'unchanged: before late-fs, no resume action',
        'change': 'bind a no-load script over /vendor/bin/vendor_modprobe.sh before its service starts',
        'readiness': 'signal vendor.all.modules.ready for diagnostic progression only; not actual driver readiness',
        'retained': 'round22 first-stage modules, gki.modprobe, C4 gating, watchdog switch, kernel and logical images',
        'deadline_sha256': hashlib.sha256(deadline.read_bytes()).hexdigest(),
        'evidence_required': 'bypass and readiness kmsg markers, module readback, continued heartbeat and return',
        'limitation': 'this is a coarse isolation of the bulk loader and its drivers; a stable result cannot identify one module or prove a usable ROM',
    }, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
