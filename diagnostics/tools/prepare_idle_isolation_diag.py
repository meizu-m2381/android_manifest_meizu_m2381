"""Prepare round20 from round19, changing only paths and CPU C4 idle gating."""
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
    names = ['init.round19.rc', 'init.staged-round19.rc', 'watch.round19.sh',
             'kmsg-wrapper.round19.sh', 'prepare-adb.round19.sh',
             'modules.blocklist.round19', 'checkpoint.round19.sh']
    for name in names:
        text = (args.previous / name).read_text().replace('round19', 'round20').replace('BOOTDIAG19', 'BOOTDIAG20')
        if name == 'init.round19.rc':
            anchor = 'on early-init\n'
            assert text.count(anchor) == 2
            writes = ''.join(f'    write /sys/devices/system/cpu/cpu{cpu}/cpuidle/state1/disable 1\n'
                             for cpu in range(8))
            text = text.replace(anchor, anchor + writes, 1)
        if name == 'checkpoint.round19.sh':
            anchor = 'tick=0\n'
            assert text.count(anchor) == 1
            # Persist the actual sysfs values in kmsg rather than trusting rc parsing.
            report = '''for cpu in 0 1 2 3 4 5 6 7; do
    node=/sys/devices/system/cpu/cpu$cpu/cpuidle/state1/disable
    value=$($BB cat "$node")
    echo "<4>BOOTDIAG20: cpu$cpu state1_disabled=$value" >/dev/kmsg
done
'''
            text = text.replace(anchor, report + anchor)
        (args.output / name.replace('round19', 'round20')).write_text(text)
    deadline = args.previous / 'bootdiag-deadline.round19'
    shutil.copyfile(deadline, args.output / 'bootdiag-deadline.round20')
    (args.output / 'plan.json').write_text(json.dumps({
        'pause': 'unchanged: before late-fs, userdata unmounted',
        'change': 'early-init disables cpuidle state1 on CPUs 0-7; WFI state0 stays enabled',
        'recovery_observed_driver': 'psci_idle / qcom-cpu-lpm',
        'state1_names': ['silver-c4'] * 3 + ['gold-c4'] * 4 + ['gold-plus-c4'],
        'kernel_and_logical_images': 'reuse round19',
        'deadline_sha256': hashlib.sha256(deadline.read_bytes()).hexdigest(),
        'expected': 'sysfs readback in kmsg; repeated heartbeat; independent 20 second return',
        'limitation': 'if gating fails or system stalls this cannot prove or exclude all power management paths',
    }, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
