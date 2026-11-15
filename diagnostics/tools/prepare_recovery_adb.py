#!/usr/bin/env python3
"""Patch a stock newc recovery copy for USB diagnostics, preserving archive metadata."""
import argparse
from pathlib import Path


AUDIT_SH = b'''#!/system/bin/sh
mkdir -p /tmp/boot-audit
mount -t pstore pstore /sys/fs/pstore
cat /proc/cmdline > /tmp/boot-audit/recovery-cmdline.txt
dmesg > /tmp/boot-audit/recovery-kmsg.txt
cp -r /sys/fs/pstore /tmp/boot-audit/pstore
mkdir -p /tmp/boot-audit/logfs
mount -t vfat -o ro /dev/block/by-name/logfs /tmp/boot-audit/logfs
chmod -R a+rX /tmp/boot-audit
'''


def encode(header, name, data):
    header = bytearray(header)
    header[54:62] = f'{len(data):08x}'.encode()
    header[94:102] = f'{len(name.encode()) + 1:08x}'.encode()
    header[102:110] = b'00000000'
    result = bytes(header) + name.encode() + b'\0'
    result += b'\0' * (-len(result) % 4)
    result += data
    result += b'\0' * (-len(result) % 4)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--show-ui', action='store_true',
                        help='Start the existing Flyme recovery UI while keeping root ADB')
    args = parser.parse_args()
    archive = args.source.read_bytes()
    offset = 0
    output = bytearray()
    changed = []
    while offset + 110 <= len(archive):
        header = archive[offset:offset + 110]
        if header[:6] != b'070701':
            raise ValueError('Expected newc archive')
        size = int(header[54:62], 16)
        namesize = int(header[94:102], 16)
        name = archive[offset + 110:offset + 110 + namesize - 1].decode()
        start = (offset + 110 + namesize + 3) & ~3
        data = archive[start:start + size]
        offset = (start + size + 3) & ~3
        if name == 'TRAILER!!!':
            # Add a script with root ownership, mode 0755, and no archive links.
            fields = [0, 0o100755, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
            script_header = b'070701' + b''.join(f'{x:08x}'.encode() for x in fields)
            output += encode(script_header, 'system/bin/m2381_audit.sh', AUDIT_SH)
            output += encode(header, name, data)
            break
        if name.removeprefix('./') == 'prop.default':
            lines = data.decode().splitlines()
            replacements = {'ro.secure': '0', 'ro.debuggable': '1', 'ro.adb.secure': '0'}
            data = ('\n'.join(key + '=' + replacements[key] if (key := line.partition('=')[0]) in replacements else line for line in lines) + '\n').encode()
            changed.append(name)
        if name.removeprefix('./') == 'system/etc/init/hw/init.rc':
            text = data.decode()
            service = 'service recovery /system/bin/recovery\n'
            if not args.show_ui:
                service += '    disabled\n'
            text = text.replace('service recovery /system/bin/recovery\n', service)
            ui_start = '    start recovery\n' if args.show_ui else ''
            ui_note = ('# Diagnostic recovery UI is enabled; do not select the wipe-data button.\n'
                       if args.show_ui else
                       '# Temporary diagnostic recovery; the Flyme UI remains disabled.\n')
            text += f'''
{ui_note}
on boot
    setprop sys.usb.config adb
{ui_start}    start m2381_audit

service m2381_audit /system/bin/sh /system/bin/m2381_audit.sh
    disabled
    oneshot
    user root
    group root
    seclabel u:r:recovery:s0
'''
            data = text.encode()
            changed.append(name)
        output += encode(header, name, data)
    if len(changed) != 2:
        raise ValueError(f'Expected exactly two patched files, found {changed}')
    output += b'\0' * (-len(output) % 512)
    args.output.write_bytes(output)
    mode = 'with Flyme recovery UI' if args.show_ui else 'ADB-only'
    print('Patched', changed, '; added system/bin/m2381_audit.sh;', mode)


if __name__ == '__main__':
    main()
