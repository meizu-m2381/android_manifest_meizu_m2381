#!/usr/bin/env python3
"""Apply M2381's existing tinyxml2 blob fixups to the synchronized vendor tree.

The extraction rules rename these blobs' dependency from the current platform
libtinyxml2 to the matching Meizu vendor ABI, but a pre-populated proprietary
tree bypasses extraction. Apply the same fixups before compiling vendorimage.
"""

import argparse
import shutil
import subprocess
from pathlib import Path


NEEDS_FIXUP = (
    "vendor/lib64/libdpps.so",
    "vendor/lib64/libsnapdragoncolor-manager.so",
    "vendor/lib64/libsynclight.so",
    "vendor/bin/poweropt-service",
    "vendor/lib64/libaodoptfeature.so",
    "vendor/lib64/libapengine.so",
    "vendor/lib64/libgamepoweroptfeature.so",
    "vendor/lib64/liblearningmodule.so",
    "vendor/lib64/liboffscreenpoweroptfeature.so",
    "vendor/lib64/libpowercallback.so",
    "vendor/lib64/libpowercore.so",
    "vendor/lib64/libpsmoptfeature.so",
    "vendor/lib64/libstandbyfeature.so",
    "vendor/lib64/libvideooptfeature.so",
)

# Reference extraction rules include these, but M2381 does not ship them.
OPTIONAL_BLOBS = {
    "vendor/lib64/libsynclight.so",
    "vendor/lib64/liboffscreenpoweroptfeature.so",
}


def run(tool: Path, *args: str) -> str:
    return subprocess.check_output([str(tool), *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aosp", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()

    vendor = args.aosp / "vendor/meizu/m2381/proprietary"
    patchelf = args.aosp / "prebuilts/extract-tools/linux-x86/bin/patchelf-0_18"
    compat_lib = vendor / "vendor/lib64/libtinyxml2_1.so"
    if not patchelf.is_file() or not compat_lib.is_file():
        raise SystemExit("缺少 patchelf 或原厂 libtinyxml2_1.so")
    soname = run(patchelf, "--print-soname", str(compat_lib))
    if soname != "libtinyxml2_1.so":
        raise SystemExit(f"原厂兼容库 SONAME 不符：{soname!r}")

    missing = [relative for relative in NEEDS_FIXUP
               if relative not in OPTIONAL_BLOBS and not (vendor / relative).is_file()]
    if missing:
        raise SystemExit(f"缺少预期 vendor blob：{missing}")

    changed = 0
    skipped = []
    for relative in NEEDS_FIXUP:
        blob = vendor / relative
        if not blob.is_file():
            skipped.append(relative)
            continue
        needed = run(patchelf, "--print-needed", str(blob)).splitlines()
        has_old = "libtinyxml2.so" in needed
        has_new = "libtinyxml2_1.so" in needed
        if has_old and has_new:
            raise SystemExit(f"{relative} 同时依赖两个 tinyxml2 SONAME，拒绝猜测")
        if has_old:
            saved = args.backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            if not saved.exists():
                shutil.copy2(blob, saved)
            subprocess.run([
                str(patchelf), "--replace-needed", "libtinyxml2.so",
                "libtinyxml2_1.so", str(blob),
            ], check=True)
            changed += 1
        elif not has_new:
            raise SystemExit(f"{relative} 不含预期 tinyxml2 依赖")
        result = run(patchelf, "--print-needed", str(blob)).splitlines()
        if "libtinyxml2_1.so" not in result or "libtinyxml2.so" in result:
            raise SystemExit(f"{relative} 修补后依赖校验失败")

    verified = len(NEEDS_FIXUP) - len(skipped)
    print(f"tinyxml2 vendor ABI fixups: {changed} patched, {verified} verified, {len(skipped)} absent")
    for relative in skipped:
        print("absent from synchronized proprietary tree:", relative)


if __name__ == "__main__":
    main()
