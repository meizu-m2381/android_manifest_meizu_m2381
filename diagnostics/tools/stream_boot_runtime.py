"""Collect live Android logs on the host across USB reconnects; never alter the phone."""
import argparse
import json
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=360)
    args = parser.parse_args()
    assert args.seconds > 0
    args.output.mkdir(parents=True, exist_ok=False)
    streams = []
    generation = 0

    def adb(*command):
        return subprocess.run([str(args.adb), '-s', args.serial, *command],
                              capture_output=True, timeout=5)

    def close_streams():
        for process, output in streams:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            output.close()
        streams.clear()

    deadline = time.monotonic() + args.seconds
    snapshot = ('echo boot_completed=$(getprop sys.boot_completed); '
                'echo zygote=$(getprop init.svc.zygote); '
                'echo surfaceflinger=$(getprop init.svc.surfaceflinger); '
                'echo deadline=$(getprop init.svc.bootdiag_deadline); '
                'pidof system_server surfaceflinger; cat /proc/uptime')
    try:
        with (args.output / 'connections.jsonl').open('w', encoding='utf-8') as journal:
            while time.monotonic() < deadline:
                try:
                    state = adb('get-state').stdout.strip()
                    if state != b'device':
                        if streams:
                            journal.write(json.dumps({'host_time': time.time(), 'event': 'disconnected'}) + '\n')
                            journal.flush()
                            print('Runtime USB disconnected; host logs retained', flush=True)
                            close_streams()
                        time.sleep(2)
                        continue
                    if not streams:
                        generation += 1
                        commands = {
                            'logcat': ['logcat', '-b', 'all', '-v', 'threadtime',
                                       'audioadsprpcd:S', 'DMABUFHEAPS:W', 'auditd:S', 'logd:S', '*:V'],
                        }
                        if adb('shell', 'id -u').stdout.strip() == b'0':
                            commands['kmsg'] = ['exec-out', 'cat', '/dev/kmsg']
                        for label, command in commands.items():
                            output = (args.output / f'connection{generation}-{label}.txt').open('wb')
                            process = subprocess.Popen([str(args.adb), '-s', args.serial, *command],
                                                       stdout=output, stderr=subprocess.STDOUT)
                            streams.append((process, output))
                        print(f'Host log streams started: connection {generation}', flush=True)
                    result = adb('shell', snapshot)
                    value = result.stdout.decode('utf-8', errors='replace')
                    journal.write(json.dumps({'host_time': time.time(), 'connection': generation,
                                              'returncode': result.returncode, 'snapshot': value,
                                              'streams': [p.poll() for p, _ in streams]}) + '\n')
                    journal.flush()
                    if 'boot_completed=1' in value.splitlines():
                        print('Boot completion observed; host capture finished', flush=True)
                        return
                except subprocess.TimeoutExpired:
                    pass
                time.sleep(3)
    finally:
        close_streams()
    print('Host capture window ended', flush=True)


if __name__ == '__main__':
    main()
