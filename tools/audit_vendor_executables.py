"""Report vendor executable ABI and imported multicall aliases without executing blobs."""

import argparse
import hashlib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vendor", type=Path)
    args = parser.parse_args()
    root = args.vendor
    hashes = {}
    elf32 = []
    for path in sorted((root / "bin").rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        rel = path.relative_to(root).as_posix()
        if data[:4] == b"\x7fELF":
            hashes.setdefault(hashlib.sha256(data).hexdigest(), []).append(rel)
            if data[4] == 1:
                elf32.append(rel)
    print("32-bit executable count:", len(elf32))
    print("\n".join(elf32))
    print("32-bit init service references:")
    for path in sorted((root / "etc/init").rglob("*.rc")):
        for line in path.read_text(errors="replace").splitlines():
            if any("/vendor/" + name in line for name in elf32):
                print(path.name + ": " + line)
    for names in hashes.values():
        if any(name in names for name in ("bin/toolbox", "bin/toybox_vendor")):
            print("multicall aliases:", " ".join(names))


if __name__ == "__main__":
    main()
