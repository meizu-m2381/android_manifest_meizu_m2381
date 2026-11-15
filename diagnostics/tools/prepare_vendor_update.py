"""Prepare a vendor-only update while preserving the verified boot images.

Run on Linux/WSL. The previous candidate is verified before use; the new top
vbmeta describes the replacement vendor. Other partitions and ramdisks stay
byte-identical, including their diagnostic init paths.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    previous = args.previous.resolve(strict=True)
    vendor = args.vendor.resolve(strict=True)
    output = args.output.resolve()
    avb = [sys.executable, str(args.aosp / "external/avb/avbtool.py")]
    entries = json.loads((previous / "manifest.json").read_text())
    for entry in entries:
        path = previous / entry["name"]
        if path.stat().st_size != entry["size"] or digest(path) != entry["sha256"]:
            raise ValueError(f"Previous candidate digest mismatch: {path}")
    subprocess.run(avb + ["verify_image", "--image", str(previous / "vbmeta.img"),
                         "--follow_chain_partitions"], check=True)
    output.mkdir(parents=True, exist_ok=False)
    preserved = {"boot.img", "init_boot.img", "vendor_boot.img", "vbmeta_system.img"}
    for entry in entries:
        name = entry["name"]
        if name in {"vendor.img", "vbmeta.img"}:
            continue
        if name in preserved:
            shutil.copy2(previous / name, output / name)
        else:
            (output / name).symlink_to(previous / name)
    shutil.copy2(vendor, output / "vendor.img")
    shutil.copy2(previous / "system.avbpubkey", output / "system.avbpubkey")
    command = avb + [
        "make_vbmeta_image", "--output", str(output / "vbmeta.img"),
        "--algorithm", "SHA256_RSA4096", "--key",
        str(args.aosp / "external/avb/test/data/testkey_rsa4096.pem"),
        "--flags", "3", "--padding_size", "65536", "--chain_partition",
        f"vbmeta_system:2:{output / 'system.avbpubkey'}",
    ]
    for name in ("boot", "init_boot", "vendor_boot", "vendor", "odm",
                 "system_dlkm", "vendor_dlkm"):
        command += ["--include_descriptors_from_image", str(output / (name + ".img"))]
    subprocess.run(command, check=True)
    with (output / "verify-avb.log").open("w") as log:
        subprocess.run(avb + ["verify_image", "--image", str(output / "vbmeta.img"),
                              "--follow_chain_partitions"], check=True,
                       stdout=log, stderr=subprocess.STDOUT)
    result = []
    for path in sorted(output.glob("*.img")):
        checksum = digest(path)
        if path.name in preserved and checksum != digest(previous / path.name):
            raise ValueError(f"Unexpected boot image change: {path}")
        result.append({"name": path.name, "size": path.stat().st_size,
                       "sha256": checksum})
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Verified vendor-only candidate:", output, flush=True)


if __name__ == "__main__":
    main()
