#!/usr/bin/env python3
"""Build an inert probe with a vendor ELF's dependency order and strong imports.

Run the output under the vendor linker namespace being tested. It relocates
all strong import names and runs dependency constructors, but never invokes
the original executable's main. Symbol versions, weak imports and dlopen paths
are outside this check; it is not a replacement for service/hardware testing.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def build(source, output, clang_bin, crt):
    data = source.read_bytes()
    if data[:4] != b'\x7fELF' or data[5] != 1:
        raise ValueError('Expected a little-endian Android ELF')
    machine = struct.unpack_from('<H', data, 18)[0]
    targets = {183: ('aarch64-linux-android37', '/system/bin/linker64'),
               40: ('armv7a-linux-androideabi37', '/system/bin/linker')}
    target, linker = targets[machine]
    readelf = clang_bin / 'llvm-readelf'
    dynamic = subprocess.check_output([str(readelf), '-d', str(source)], text=True)
    needed = re.findall(r'Shared library: \[(.*?)\]', dynamic)
    if not needed or any(Path(name).name != name for name in needed):
        raise ValueError('Expected bare DT_NEEDED library names')
    table = subprocess.check_output([str(readelf), '--dyn-syms', '--wide', str(source)], text=True)
    names = []
    for line in table.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[4] == 'GLOBAL' and fields[6] == 'UND':
            if fields[3] not in ('FUNC', 'OBJECT', 'NOTYPE'):
                raise ValueError(f'Unsupported import type: {fields[3]}')
            name = fields[7].split('@')[0]
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9.$]*', name):
                raise ValueError(f'Unsupported import name: {name}')
            if name not in names:
                names.append(name)
    if not names:
        raise ValueError('No strong imports found')
    output.parent.mkdir(parents=True, exist_ok=True)
    clang = str(clang_bin / 'clang')
    with tempfile.TemporaryDirectory(prefix='vendor-relocation-') as temporary:
        stage = Path(temporary)
        code = stage / 'probe.c'
        code.write_text('\n'.join(
            f'extern char symbol_{i}[] __asm__("{name}");' for i, name in enumerate(names))
            + '\nvoid * volatile references[] = {'
            + ','.join(f'symbol_{i}' for i in range(len(names)))
            + '};\nint main(void) { return references[0] ? 0 : 1; }\n')
        stubs = []
        for name in needed:
            stub = stage / name
            subprocess.run([clang, '--target=' + target, '-fuse-ld=lld', '-nostdlib', '-shared',
                            '-Wl,-soname,' + name, '-x', 'c', '/dev/null', '-o', str(stub)], check=True)
            stubs.append(str(stub))
        binary = stage / 'probe'
        subprocess.run([clang, '--target=' + target, '-fuse-ld=lld', '-nostdlib', '-fPIE', '-pie',
                        '-Wl,--pack-dyn-relocs=none', '-Wl,--unresolved-symbols=ignore-all',
                        '-Wl,-dynamic-linker,' + linker, str(crt), str(code),
                        '-Wl,--no-as-needed', *stubs, '-o', str(binary)], check=True)
        actual = subprocess.check_output([str(readelf), '-d', str(binary)], text=True)
        if re.findall(r'Shared library: \[(.*?)\]', actual) != needed:
            raise ValueError('Probe dependency order differs from input')
        actual_table = subprocess.check_output(
            [str(readelf), '--dyn-syms', '--wide', str(binary)], text=True)
        imports = {fields[7].split('@')[0] for line in actual_table.splitlines()
                   if len(fields := line.split()) >= 8
                   and fields[4] == 'GLOBAL' and fields[6] == 'UND'}
        if not set(names).issubset(imports):
            raise ValueError('Linker dropped a required probe relocation')
        output.write_bytes(binary.read_bytes())
        output.chmod(0o755)
    return {'source': str(source), 'strong_import_names': len(names), 'needed': needed,
            'limits': 'No symbol-version, weak-import, dlopen or daemon-main validation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clang-bin', type=Path, required=True)
    parser.add_argument('--crt', type=Path, required=True,
                        help='Matching bionic crtbegin_dynamic.o from this product build')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.clang_bin, args.crt), indent=2))


if __name__ == '__main__':
    main()
