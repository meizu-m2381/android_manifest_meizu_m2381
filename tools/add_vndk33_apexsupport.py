"""Expose the LLNDK dependency required by the current VNDK33 libbinder.

The Android 16 VNDK33 snapshot omits libapexsupport from its frozen LLNDK
lists, while the shipped VNDK33 libbinder links against that system LLNDK.
"""

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aosp", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()

    base = args.aosp / "prebuilts/vndk/v33"
    for arch in ("arm", "arm64"):
        path = base / arch / "configs/llndk.libraries.txt"
        original = path.read_text()
        lines = original.splitlines()
        anchor = "libandroid_net.so"
        assert lines.count(anchor) == 1, f"Unexpected LLNDK list: {path}"
        if "libapexsupport.so" in lines:
            assert lines.count("libapexsupport.so") == 1
            print("already present", path)
            continue
        lines.insert(lines.index(anchor) + 1, "libapexsupport.so")
        updated = "\n".join(lines) + "\n"

        saved = args.backup / path.relative_to(args.aosp)
        saved.parent.mkdir(parents=True, exist_ok=True)
        if not saved.exists():
            shutil.copy2(path, saved)
        path.write_text(updated)
        print("updated", path)


if __name__ == "__main__":
    main()
