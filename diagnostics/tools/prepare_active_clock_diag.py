"""Prepare round21, retaining round20 C4 gating and using an active timer."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    names = ['init.round20.rc', 'init.staged-round20.rc', 'watch.round20.sh',
             'kmsg-wrapper.round20.sh', 'prepare-adb.round20.sh',
             'modules.blocklist.round20', 'checkpoint.round20.sh']
    for name in names:
        text = (args.previous / name).read_text().replace('round20', 'round21').replace('BOOTDIAG20', 'BOOTDIAG21')
        (args.output / name.replace('round20', 'round21')).write_text(text)
    (args.output / 'plan.json').write_text(json.dumps({
        'pause': 'unchanged: before late-fs',
        'C4_disabled': 'unchanged: state1 on all eight CPUs',
        'change': 'replace sleeping deadline with static monotonic-clock busy polling and nonblocking kmsg heartbeat',
        'duration_seconds': 20,
        'limitation': 'busy polling itself changes CPU activity; failure still needs logs and success does not prove a specific root cause',
    }, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
