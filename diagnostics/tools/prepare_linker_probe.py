"""Package a read-only bootstrap linker replay for the diagnostic recovery.

Reproduce Android's pre-linkerconfig system/odm/vendor search order. This checks
loading only (--list), never starts the service or touches userdata.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    images = args.images
    built = args.aosp / "out/target/product/m2381"
    reader = sorted((args.aosp / "prebuilts/clang/host/linux-x86").glob("clang-r*/bin/llvm-readelf"))[-1]
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    root = output / "root"
    search = [(images / "system/system/lib64", "system/lib64"),
              (images / "odm/lib64", "odm/lib64"),
              (images / "vendor/lib64", "vendor/lib64")]
    installed = {}

    def copy(source, target):
        dest = root / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink() and str(source.readlink()).startswith("/apex/"):
            source = built / str(source.readlink()).lstrip("/")
        shutil.copy2(source, dest)
        return dest

    def dependencies(path):
        text = subprocess.check_output([str(reader), "-d", str(path)], text=True)
        return re.findall(r"\(NEEDED\).*?\[([^]]+)\]", text)

    program = copy(images / "vendor/bin/vndservicemanager", "vendor/bin/vndservicemanager")
    copy(built / "apex/com.android.runtime/bin/linker64", "system/bin/linker64")
    pending = dependencies(program)
    while pending:
        name = pending.pop()
        if name in installed:
            continue
        for directory, target in search:
            source = directory / name
            if source.exists() or source.is_symlink():
                path = copy(source, target + "/" + name)
                installed[name] = target + "/" + name
                pending.extend(dependencies(path))
                break
        else:
            raise RuntimeError("Unresolved bootstrap dependency: " + name)
    (output / "manifest.json").write_text(json.dumps(installed, indent=2) + "\n")
    with tarfile.open(output / "probe.tar", "w") as archive:
        archive.add(root, arcname=".")
    print("Probe libraries:", len(installed), "archive bytes:", (output / "probe.tar").stat().st_size)


if __name__ == "__main__":
    main()
