#!/usr/bin/env python3
"""Verify/reproduce the M2381 stock-module PD/USB ICL compatibility fix.

Never edits stock inputs. Unknown inputs or conflicting outputs are rejected.
This is a binary compatibility fix, not a source-built replacement driver.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import tempfile

STOCK_SHA256 = '8da01509b610ba864add19b06a5db51b6d3ee4d5bddf696e2d9a633c21288b4f'
FIXED_SHA256 = '57676136fb51ce8508053c9d10784a170d0c202366fc0f8a3b6e624b894c0874'
SOURCE = Path('vendor/meizu/m2381/proprietary/vendor_dlkm/lib/modules/qti_battery_charger.ko')
OUTPUT = Path('vendor/meizu/m2381/compat/vendor_dlkm/lib/modules/qti_battery_charger.ko')
RULE = 'LOCAL_SRC_FILES := proprietary/vendor_dlkm/lib/modules/qti_battery_charger.ko'
FIXED_RULE = 'LOCAL_SRC_FILES := compat/vendor_dlkm/lib/modules/qti_battery_charger.ko'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def transform(data):
    if digest(data) != STOCK_SHA256:
        raise ValueError('Unknown stock charger module; obtain the pinned input, do not force this fix')
    if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
        raise ValueError('Expected an ELF64 little-endian AArch64 module')
    shoff = struct.unpack_from('<Q', data, 40)[0]
    entsize, count, names_index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff+i*entsize) for i in range(count)]
    names_header = sections[names_index]
    names = data[names_header[4]:names_header[4]+names_header[5]]
    text = [s for s in sections if names[s[0]:].split(b'\0', 1)[0] == b'.text']
    if len(text) != 1 or text[0][5] < 0x38f8:
        raise ValueError('Unexpected text section')
    offset = text[0][4] + 0x38f4
    # usb_psy_set_icl: mov w9,#0x4a -> #0x0a. Keep SDP/CDP, exclude PD.
    # PD current stays under the firmware contract and thermal votes; no forced ICL.
    before, after = struct.pack('<I', 0x52800949), struct.pack('<I', 0x52800149)
    if data[offset:offset+4] != before:
        raise ValueError('Unexpected instruction at usb_psy_set_icl+0x80')
    fixed = data[:offset] + after + data[offset+4:]
    if digest(fixed) != FIXED_SHA256 or len(fixed) != len(data):
        raise ValueError('Output digest mismatch')
    return fixed


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False) as f:
            tmp = Path(f.name)
            f.write(data)
        tmp.chmod(0o644)
        tmp.replace(path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def configure(root, apply=False):
    source, output = root/SOURCE, root/OUTPUT
    fixed = transform(source.read_bytes())
    # A second bundled copy is used by the first-stage module list. Preserve it.
    extra = root/'device/meizu/m2381/modules_prebuilt/qti_battery_charger.ko'
    if extra.exists() and digest(extra.read_bytes()) != STOCK_SHA256:
        raise ValueError('First-stage stock input has a different digest')
    makefile = root/'vendor/meizu/m2381/Android.mk'
    text = makefile.read_text(encoding='utf-8')
    if text.count(RULE)+text.count(FIXED_RULE) != 1:
        raise ValueError('Expected exactly one charger module install rule')
    if output.exists() and output.read_bytes() != fixed:
        raise ValueError('Conflicting compatibility output; refusing to overwrite')
    if apply:
        if not output.exists():
            atomic_write(output, fixed)
        if RULE in text:
            atomic_write(makefile, text.replace(RULE, FIXED_RULE).encode())
    elif not output.exists() or FIXED_RULE not in text:
        raise ValueError('PD ICL compatibility fix is not installed; review docs/charging.md and use --apply')
    print('PD ICL compatibility: verified', FIXED_SHA256)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true', help='Create the separate compatibility copy and select it for packaging')
    args = parser.parse_args()
    try:
        configure(args.root, args.apply)
    except (ValueError, OSError, struct.error, IndexError) as error:
        parser.exit(1, f'PD ICL compatibility: {error}\n')


if __name__ == '__main__':
    main()
