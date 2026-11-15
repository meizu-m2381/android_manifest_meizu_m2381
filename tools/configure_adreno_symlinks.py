"""Replace duplicate Adreno root library copies with device-owned aliases.

The EGL loader opens lib*/egl explicitly, while the driver's dependencies use
lib*. Different inodes create separate driver instances and split GL state.
Keep the canonical binaries in egl/ and install relative root symlinks.
"""

import argparse
import hashlib
from pathlib import Path

from configure_connectivity import configure


ALIASES = {
    f"vendor/{abi}/{name}": f"vendor/{abi}/egl/{name}"
    for abi in ("lib", "lib64")
    for name in ("libEGL_adreno.so", "libGLESv2_adreno.so")
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    args = parser.parse_args()
    blobs = args.tree / "vendor/meizu/m2381/proprietary"
    for alias, target in ALIASES.items():
        canonical = blobs / target
        if not canonical.is_file():
            raise ValueError(f"Missing canonical driver: {canonical}")
        original = blobs / alias
        if original.exists():
            if hashlib.sha256(original.read_bytes()).digest() != hashlib.sha256(canonical.read_bytes()).digest():
                raise ValueError(f"Alias differs from canonical driver: {original}")
    configure(args.tree, set(ALIASES))


if __name__ == "__main__":
    main()
