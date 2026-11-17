#!/usr/bin/env python3
"""Restore the saved entry and length of the two identified M2381 KP 0.12 images.

Matches bmax121/KernelPatch tag 0.12.0, tools/patch.c unpatch_img and
kernel/include/preset.h (commit 57d487090add7e25e98cfb8d569d999c14f30352).
Only a new output is written. A restored image still needs device validation.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path


IDENTIFIED = {
    "02d61bb0f4958e9a3129a480b4d391b925e2d6671b1b7ce15978727bc4e6b763":
        "0e04acb26a3e1c632b06c7818c43b33526b09d11996aa1a44809e6718daaa413",
    "6874d073b39f2b32b38b316d294356b3a2c37f1d6aada99ee0fffe34503c9e69":
        "0f082b0fa6d21007a24b6a11976a08867be6612e65cfe1db29bbc08e2462648e",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        parser.error("Output and report must be new files")
    image = args.input.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if digest not in IDENTIFIED:
        parser.error("Unrecognized kernel; refusing to infer patch layout")
    magic = b"KP1158\0\0"
    assert image.count(magic) == 1
    offset = image.index(magic)
    assert image[offset + 8:offset + 12] == bytes((0, 0, 12, 0))
    setup = offset + 64
    size = struct.unpack_from("<Q", image, setup + 8)[0]
    assert (size + 4095) & ~4095 == offset
    # v0.12: 13 eight-byte fields, then five eight-byte map symbols.
    backup = image[setup + 104 + 40:setup + 104 + 40 + 8]
    restored = backup + image[8:size]
    assert restored[56:60] == b"ARMd" and len(restored) == size
    assert magic not in restored
    restored_digest = hashlib.sha256(restored).hexdigest()
    assert restored_digest == IDENTIFIED[digest]
    args.output.write_bytes(restored)
    report = {
        "source_sha256": digest,
        "restored_sha256": restored_digest,
        "source_bytes": len(image), "restored_bytes": size,
        "kernelpatch_version": "0.12.0", "preset_offset": offset,
        "changed_ranges": ["entry bytes 0..7 restored", "appended patch removed"],
        "original_preserved": True, "device_tested": False,
        "official_reference_commit": "57d487090add7e25e98cfb8d569d999c14f30352",
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print("Verified restored kernel:", restored_digest)


if __name__ == "__main__":
    main()
