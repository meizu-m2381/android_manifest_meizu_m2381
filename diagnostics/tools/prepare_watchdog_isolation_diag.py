"""Prepare round22 from round21 with the driver's watchdog disable switch."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


WATCHDOG_NODE = '/sys/devices/platform/hypervisor/hypervisor:qcom,gh-watchdog/disable'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    names = ['init.round21.rc', 'init.staged-round21.rc', 'watch.round21.sh',
             'kmsg-wrapper.round21.sh', 'prepare-adb.round21.sh',
             'modules.blocklist.round21', 'checkpoint.round21.sh']
    for name in names:
        content = (args.previous / name).read_text()
        content = content.replace('round21', 'round22').replace('BOOTDIAG21', 'BOOTDIAG22')
        if name == 'init.round21.rc':
            anchor = 'on early-init\n'
            assert content.count(anchor) == 2
            content = content.replace(anchor, anchor +
                                      f'    write {WATCHDOG_NODE} 1\n', 1)
        if name == 'checkpoint.round21.sh':
            anchor = 'checkpoint_before_late_fs\n'
            assert content.count(anchor) == 1
            report = (f'watchdog_disabled=$($BB cat {WATCHDOG_NODE})\n'
                      'echo "<4>BOOTDIAG22: watchdog_disabled=$watchdog_disabled" >/dev/kmsg\n')
            content = content.replace(anchor, anchor + report)
        (args.output / name.replace('round21', 'round22')).write_text(content)
    deadline = args.previous / 'bootdiag-deadline.round21'
    shutil.copyfile(deadline, args.output / 'bootdiag-deadline.round22')
    (args.output / 'plan.json').write_text(json.dumps({
        'pause': 'unchanged: before late-fs, userdata unmounted',
        'C4_disabled': 'unchanged: state1 on all eight CPUs',
        'change': f'early-init writes 1 to {WATCHDOG_NODE}',
        'evidence_required': 'driver deactivated message and watchdog_disabled=1 in kmsg',
        'kernel_modules_and_logical_images': 'unchanged; do not remove watchdog dependencies',
        'deadline_sha256': hashlib.sha256(deadline.read_bytes()).hexdigest(),
        'limitation': 'disabling watchdog may stop automatic reset without restoring scheduling; '
                      'a stuck logo requires manual bootloader entry and is not a successful boot',
    }, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
