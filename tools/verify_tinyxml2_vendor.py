#!/usr/bin/env python3
"""Check patched ELF dependencies and tinyxml2 imports in an extracted vendor image."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from apply_tinyxml2_vendor_fixups import NEEDS_FIXUP, OPTIONAL_BLOBS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tinyxml_symbols(path):
    output = subprocess.check_output(["readelf", "--dyn-syms", "--wide", str(path)], text=True)
    imports, exports = set(), set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":"):
            continue
        name = fields[7].split("@")[0]
        if "tinyxml2" not in name:
            continue
        if fields[6] == "UND" and fields[4] == "GLOBAL":
            imports.add(name)
        elif fields[6] != "UND" and fields[4] in ("GLOBAL", "WEAK"):
            exports.add(name)
    return imports, exports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    tool = args.aosp / "prebuilts/extract-tools/linux-x86/bin/patchelf-0_18"
    source = args.aosp / "vendor/meizu/m2381/proprietary"
    compat = args.vendor / "lib64/libtinyxml2_1.so"
    exports = tinyxml_symbols(compat)[1]
    assert exports, "No tinyxml2 exports found"
    assert digest(compat) == digest(source / "vendor/lib64/libtinyxml2_1.so")
    report = {"compat_library_sha256": digest(compat), "checked": [], "absent": []}
    for relative in NEEDS_FIXUP:
        blob = args.vendor / relative.removeprefix("vendor/")
        if not blob.is_file():
            assert relative in OPTIONAL_BLOBS, relative
            assert not (source / relative).exists(), relative
            report["absent"].append(relative)
            continue
        assert digest(blob) == digest(source / relative), relative
        needed = subprocess.check_output([str(tool), "--print-needed", str(blob)], text=True).splitlines()
        assert "libtinyxml2_1.so" in needed and "libtinyxml2.so" not in needed, relative
        imports = tinyxml_symbols(blob)[0]
        missing = imports - exports
        assert not missing, (relative, sorted(missing))
        report["checked"].append({"path": relative, "tinyxml2_imports": len(imports), "sha256": digest(blob)})
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Actual vendor image verified: {len(report['checked'])} blobs, no missing tinyxml2 symbols")


if __name__ == "__main__":
    main()
