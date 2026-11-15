"""Retain runtime diagnostics through orderly init shutdown without changing boot flow."""
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
    args = parser.parse_args()
    old, new = args.previous_round, args.round
    assert new > old >= 37
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
    assert 'printk_devkmsg' not in text
    text = text.replace('on early-init\n',
                        'on early-init\n    write /proc/sys/kernel/printk_devkmsg on\n', 1)
    for service in ['bootdiag_kmsg', 'bootdiag_logcat']:
        pattern = r'(^service ' + service + r' [^\n]+\n)'
        text, count = re.subn(pattern, r'\1    shutdown critical\n', text, flags=re.M)
        assert count == 1
    text += f'\non shutdown\n    write /dev/kmsg "<4>BOOTDIAG{new}: shutdown_trigger"\n'
    contents[entry] = text.encode('utf-8')
    args.output.mkdir(exist_ok=False)
    for name, data in contents.items():
        (args.output / name).write_bytes(data)
    (args.output / 'plan.json').write_text(json.dumps({
        'previous_round': old, 'round': new,
        'change': 'disable devkmsg write rate limit; retain kmsg/logcat through init shutdown',
        'retained': 'normal Android init, tz_log blocklist, C4 gating, kernel and logical images',
        'deadline': 'unchanged orderly init reboot at 180 seconds; no raw restart2',
        'userdata': 'normal Android mounting; no wipe or format added',
        'evidence': 'round37 mounted data then init sent SIGTERM to diagnostic services; persisted reason recovery',
    }, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
