"""Check stock vendor android::base references against installed libbase exports.

Reads ELF dynamic tables for both architectures; never executes vendor blobs.
This checks symbol availability, not complete linker namespace compatibility.
"""

import argparse
import json
import struct
from pathlib import Path


def symbols(path):
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        return None
    if struct.unpack_from("<H", data, 18)[0] not in (40, 183):
        return None  # DSP/firmware ELF does not use the Android process runtime.
    assert data[5] == 1, f"Unsupported ELF endianness: {path}"
    bits = data[4]
    if bits == 2:
        offset = struct.unpack_from("<Q", data, 40)[0]
        stride, count = struct.unpack_from("<HH", data, 58)
        section_fmt, symbol_fmt = "<IIQQQQIIQQ", "<IBBHQQ"
    elif bits == 1:
        offset = struct.unpack_from("<I", data, 32)[0]
        stride, count = struct.unpack_from("<HH", data, 46)
        section_fmt, symbol_fmt = "<IIIIIIIIII", "<IIIBBH"
    else:
        raise ValueError(f"Unsupported ELF class: {path}")
    sections = [struct.unpack_from(section_fmt, data, offset + i * stride)
                for i in range(count)]
    assert sections, f"ELF has no section table: {path}"
    undefined, defined = set(), set()
    for section in sections:
        if section[1] != 11:
            continue
        string_section = sections[section[6]]
        strings = data[string_section[4]:string_section[4] + string_section[5]]
        for pos in range(section[4], section[4] + section[5], section[9]):
            sym = struct.unpack_from(symbol_fmt, data, pos)
            name, info, other, index = ((sym[0], sym[1], sym[2], sym[3]) if bits == 2
                                        else (sym[0], sym[3], sym[4], sym[5]))
            if info >> 4 not in (1, 2):
                continue
            text = strings[name:strings.find(b"\0", name)].decode(errors="replace")
            if not text.startswith(("_ZN7android4base", "_ZNK7android4base")):
                continue
            if index == 0 and info >> 4 == 1:
                undefined.add(text)
            elif index != 0 and other & 3 in (0, 3):
                defined.add(text)
    return bits, undefined, defined


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vendor", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lib32", type=Path)
    parser.add_argument("--lib64", type=Path)
    parser.add_argument("--only-64", action="store_true")
    args = parser.parse_args()
    libraries = {2: args.lib64 or args.vendor / "lib64/libbase.so"}
    if not args.only_64:
        libraries[1] = args.lib32 or args.vendor / "lib/libbase.so"
    exports = {bits: symbols(path)[2] for bits, path in libraries.items()}
    failures, references = [], 0
    for directory in ("bin", "lib", "lib64"):
        for path in sorted((args.vendor / directory).rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            result = symbols(path)
            if not result:
                continue
            bits, undefined, _ = result
            if bits not in exports:
                continue
            if undefined:
                references += 1
            missing = sorted(undefined - exports[bits])
            if missing:
                failures.append({"path": path.relative_to(args.vendor).as_posix(),
                                 "missing": missing})
    report = {"referencing_elf_count": references, "missing_symbols": failures}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
