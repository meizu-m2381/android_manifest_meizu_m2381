#!/usr/bin/env python3
"""Request the unwrapped HIDL mapper before casting to QTI extensions.

The stock EGL driver calls IMapper::getService(false), then casts the returned
BsMapper to IQtiMapper. The wrapper advertises its implementation's interfaces
but has no QTI extension slots. getStub=true returns the actual implementation.
Only the verified Meizu driver builds below are supported. Vulkan's ARM64
driver uses the same unsafe cast; its round41 crash calls BsMapper vtable+0xf0.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


SPECS = (
    ("lib64", "84a6608fcb86a9823de54057be3bc0be44712dbb6dc6dbd7aa46e638b7466b2d",
     bytes.fromhex("e1031f2a"), bytes.fromhex("21008052"),
     ((0xfd78, "e1031f2a85170094"),
      (0xff98, "e1031f2a09170094"),
      (0x10074, "e1031f2ade160094"))),
    ("lib", "43e6ceeed6d1b44850f87a2e7269a552cc82af66826ffbefce3c0275f478af2c",
     bytes.fromhex("0022"), bytes.fromhex("0122"),
     ((0x4ff6, "0022304607f00aeb"),
      (0x514a, "0022304607f070ea"),
      (0x51ec, "0022384607f02eea"))),
)

VULKAN_SPECS = (
    ("lib64", "4a0a7095e26f20fdf3531a16b44e52d9cecccc6b88659d61c71118da0b75f035",
     bytes.fromhex("e1031f2a"), bytes.fromhex("21008052"),
     ((0x215f9c, "e1031f2a1ecc0194"),
      (0x2166bc, "e1031f2a68ca0194"),
      (0x2167a0, "e1031f2a3bca0194"))),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path, spec):
    _, original_sha, old, new, points = spec
    data = path.read_bytes()
    restored = bytearray(data)
    states = []
    for offset, context_hex in points:
        context = bytes.fromhex(context_hex)
        current = data[offset:offset + len(old)]
        if current not in (old, new):
            raise ValueError(f"Unexpected instruction: {path} at {offset:#x}")
        if data[offset + len(old):offset + len(context)] != context[len(old):]:
            raise ValueError(f"Unexpected call context: {path} at {offset:#x}")
        restored[offset:offset + len(old)] = old
        states.append(current == new)
    if sha(restored) != original_sha or len(set(states)) != 1:
        raise ValueError(f"Unknown or partially patched driver: {path}")
    patched = bytearray(restored)
    for offset, _ in points:
        patched[offset:offset + len(new)] = new
    return data, bytes(patched), states[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--check-vendor", type=Path,
                        help="Check extracted vendor image instead of patching sources")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--driver", choices=("egl", "vulkan"), default="egl",
                        help="Vulkan currently supports the verified ARM64 blob only")
    args = parser.parse_args()
    root = args.check_vendor or args.aosp / "vendor/meizu/m2381/proprietary/vendor"
    plan = []
    specs = SPECS if args.driver == "egl" else VULKAN_SPECS
    for spec in specs:
        relative = Path(spec[0]) / ("egl/eglSubDriverAndroid.so" if args.driver == "egl"
                                    else "hw/vulkan.adreno.so")
        path = root / relative
        data, patched, done = inspect(path, spec)
        if args.check_vendor and not done:
            raise ValueError(f"Image still contains unpatched driver: {path}")
        plan.append((relative, path, data, patched, done, spec))
    if not args.check_vendor:
        if args.backup is None:
            parser.error("--backup is required when patching sources")
        for relative, path, data, patched, done, _ in plan:
            if done:
                continue
            saved = args.backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            if saved.exists():
                if saved.read_bytes() != data:
                    raise ValueError(f"Backup differs from original: {saved}")
            else:
                shutil.copy2(path, saved)
            path.write_bytes(patched)
    report = [{"path": relative.as_posix(), "original_sha256": spec[1],
               "patched_sha256": sha(patched),
               "file_offsets": [hex(point[0]) for point in spec[4]],
               "previously_patched": done}
              for relative, _, _, patched, done, spec in plan]
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{args.driver.upper()} mapper getStub=true: {len(specs)} architectures, "
          f"{sum(len(spec[4]) for spec in specs)} verified call sites")


if __name__ == "__main__":
    main()
