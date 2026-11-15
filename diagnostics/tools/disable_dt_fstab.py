#!/usr/bin/env python3
"""Disable only legacy DT fstab, using the checkout's prebuilt libfdt."""
import argparse
import ctypes
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--libfdt', type=Path, required=True)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    fdt = ctypes.CDLL(str(args.libfdt.resolve()))
    fdt.fdt_check_header.argtypes = [ctypes.c_void_p]
    fdt.fdt_open_into.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    fdt.fdt_path_offset.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fdt.fdt_setprop.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p,
                              ctypes.c_void_p, ctypes.c_int]
    fdt.fdt_pack.argtypes = [ctypes.c_void_p]
    source = ctypes.create_string_buffer(data)
    if fdt.fdt_check_header(source) or int.from_bytes(data[4:8], 'big') != len(data):
        raise ValueError('Expected one valid, unpadded DTB')
    output = ctypes.create_string_buffer(len(data) + 4096)
    result = fdt.fdt_open_into(source, output, len(output))
    if result:
        raise ValueError(f'fdt_open_into: {result}')
    node = fdt.fdt_path_offset(output, b'/firmware/android/fstab')
    if node < 0:
        raise ValueError('No legacy DT fstab node')
    result = fdt.fdt_setprop(output, node, b'status', b'disabled\0', 9)
    if result:
        raise ValueError(f'fdt_setprop: {result}')
    result = fdt.fdt_pack(output)
    if result:
        raise ValueError(f'fdt_pack: {result}')
    length = int.from_bytes(output.raw[4:8], 'big')
    args.output.write_bytes(output.raw[:length])
    print(f'Wrote {length} bytes to {args.output}')


if __name__ == '__main__':
    main()
