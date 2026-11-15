"""Build the standalone GLES pixel probe using an existing Linux/WSL AOSP build.

Only emits diagnostics into the requested output folder; does not install it
in the ROM. Run the two executables through root ADB on the target device.
"""

import argparse
from pathlib import Path
import subprocess


def unique(paths):
    found = list(paths)
    if len(found) != 1:
        raise ValueError(f"Expected one built bionic input, found: {found}")
    return found[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clang", type=Path, required=True,
                        help="Path to the AOSP build's installed host clang executable")
    args = parser.parse_args()
    aosp = args.aosp.resolve(strict=True)
    clang = args.clang.resolve(strict=True)
    bionic = aosp / "out/soong/.intermediates/bionic"
    source = Path(__file__).with_name("egl_probe.c")
    args.output.mkdir(parents=True, exist_ok=True)
    for abi, target, linker in (
        ("arm64", "aarch64-linux-android35", "/system/bin/linker64"),
        ("arm", "armv7a-linux-androideabi35", "/system/bin/linker"),
    ):
        crt = unique(p / "crtbegin_dynamic.o" for p in (bionic / "libc/crtbegin_dynamic").iterdir()
                     if p.name.startswith("android_" + abi + "_") and "_apex" not in p.name)
        libraries = []
        for name in ("libc", "libdl"):
            libraries.append(unique((bionic / name / name).glob(
                "android_" + abi + "_*_shared/" + name + ".so")))
        subprocess.run([
            str(clang), "--target=" + target,
            "-Wall", "-Wextra", "-Werror", "-fuse-ld=lld", "-nostdlib", "-fPIE", "-pie",
            "-Wl,-dynamic-linker," + linker, str(crt), str(source),
            *map(str, libraries), "-o", str(args.output / ("egl-probe-" + abi)),
        ], check=True)
        print("Built GLES probe:", abi, flush=True)


if __name__ == "__main__":
    main()
