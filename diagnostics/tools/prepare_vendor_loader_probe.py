"""Derive a bounded vendor-loader diagnostic from a verified previous round."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-round', type=int, required=True)
    parser.add_argument('--round', type=int, required=True)
    parser.add_argument('--restore-watchdog', action='store_true')
    parser.add_argument('--module-list', type=Path,
                        help='Explicit module names to load sequentially using modprobe dependencies')
    args = parser.parse_args()
    assert args.round > args.previous_round >= 23
    assert args.restore_watchdog or args.module_list, 'Specify one diagnostic change'
    assert not (args.restore_watchdog and args.module_list), 'Change only one factor per round'
    old, new = args.previous_round, args.round
    args.output.mkdir(parents=True, exist_ok=False)
    names = [f'init.round{old}.rc', f'init.staged-round{old}.rc', f'watch.round{old}.sh',
             f'kmsg-wrapper.round{old}.sh', f'prepare-adb.round{old}.sh',
             f'modules.blocklist.round{old}', f'checkpoint.round{old}.sh',
             f'vendor-modprobe.round{old}.sh']
    for name in names:
        content = (args.previous / name).read_text()
        content = content.replace(f'round{old}', f'round{new}').replace(f'BOOTDIAG{old}', f'BOOTDIAG{new}')
        if args.restore_watchdog and name == f'init.round{old}.rc':
            line = '    write /sys/devices/platform/hypervisor/hypervisor:qcom,gh-watchdog/disable 1\n'
            assert content.count(line) == 1
            content = content.replace(line, '')
        (args.output / name.replace(f'round{old}', f'round{new}')).write_text(content)
    selected = None
    if args.module_list:
        selected = [s.strip() for s in args.module_list.read_text().splitlines()
                    if s.strip() and not s.lstrip().startswith('#')]
        assert selected and len(selected) == len(set(selected))
        assert all(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', s) for s in selected)
        script = f'''#!/vendor/bin/sh
echo "<4>BOOTDIAG{new}: vendor_selected_load_start" >/dev/kmsg
'''
        for module in selected:
            script += f'''echo "<4>BOOTDIAG{new}: before_module={module}" >/dev/kmsg
/vendor/bin/modprobe -b -d /vendor_dlkm/lib/modules -a {module}
result=$?
echo "<4>BOOTDIAG{new}: after_module={module} result=$result" >/dev/kmsg
'''
        script += f'''if ! /vendor/bin/setprop vendor.all.modules.ready 1; then
    echo "<3>BOOTDIAG{new}: diagnostic_readiness_failed" >/dev/kmsg
    exit 1
fi
echo "<4>BOOTDIAG{new}: diagnostic_readiness_signalled" >/dev/kmsg
exit 0
'''
        (args.output / f'vendor-modprobe.round{new}.sh').write_text(script)
        shutil.copyfile(args.module_list, args.output / 'selected-modules.txt')
    deadline = args.previous / f'bootdiag-deadline.round{old}'
    shutil.copyfile(deadline, args.output / f'bootdiag-deadline.round{new}')
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old,
        'round': new,
        'change': 'restore normal watchdog' if args.restore_watchdog else 'load selected vendor drivers sequentially',
        'selected_modules': selected,
        'pause': 'unchanged: before late-fs, no resume action',
        'deadline_sha256': hashlib.sha256(deadline.read_bytes()).hexdigest(),
        'limitation': 'modprobe may load dependencies outside the selected list; sequential loading changes timing; '
                      'diagnostic readiness is not real driver readiness and this is not a usable ROM',
    }, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
