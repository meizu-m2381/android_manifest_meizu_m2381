"""Build a verified AVB chain using current images and a proven diagnostic ramdisk.

Run after the image build completes. Preserve all vendor cpio entries and change
only the diagnostic round name. The previous candidate supplies the DT and
bootconfig; current build outputs supply all other partitions, including init.
"""

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from prepare_recovery_adb import encode
from inspect_boot_cpio import read_cpio


def rename_round(archive, name, script):
    offset, changed = 0, 0
    output = bytearray()
    while offset + 110 <= len(archive):
        header = archive[offset:offset + 110]
        assert header[:6] == b"070701"
        size = int(header[54:62], 16)
        namesize = int(header[94:102], 16)
        entry = archive[offset + 110:offset + 110 + namesize - 1].decode()
        start = (offset + 110 + namesize + 3) & ~3
        data = archive[start:start + size]
        offset = (start + size + 3) & ~3
        if entry.removeprefix("./") == "first_stage.sh":
            import re
            data, count = re.subn(rb"pixelos-round[0-9]+", name.encode(), script)
            assert count >= 1
            changed += 1
        output += encode(header, entry, data)
        if entry == "TRAILER!!!":
            break
    assert changed == 1
    output += b"\0" * (-len(output) % 512)
    before = {entry: (mode, data) for entry, mode, data in read_cpio(archive)}
    after = {entry: (mode, data) for entry, mode, data in read_cpio(output)}
    assert before.keys() == after.keys()
    differences = [entry for entry in before if before[entry] != after[entry]]
    assert len(differences) == 1 and differences[0].removeprefix("./") == "first_stage.sh"
    assert before[differences[0]][0] == after[differences[0]][0]
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--first-stage-script", type=Path,
                        default=Path(__file__).with_name("first_stage_diag.sh"))
    parser.add_argument("--init-rc", help="Temporary second-stage init entry point")
    parser.add_argument("--reuse-previous-images", action="store_true",
                        help="Keep the previous tested system and kernel images")
    parser.add_argument("--vendor-image", type=Path,
                        help="Replace only vendor while retaining other previous images")
    parser.add_argument("--kernel-image", type=Path,
                        help="Use an independently verified ARM64 Image for a kernel-only diagnostic")
    args = parser.parse_args()
    aosp, out = args.aosp.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    images = args.previous if args.reuse_previous_images else aosp / "out/target/product/m2381"
    mkboot = aosp / "system/tools/mkbootimg"
    avb = [sys.executable, str(aosp / "external/avb/avbtool.py")]
    keys = aosp / "external/avb/test/data"

    def run(command, **kwargs):
        return subprocess.run(list(map(str, command)), check=True, **kwargs)

    logical = ["system", "system_ext", "product", "vendor", "odm", "system_dlkm", "vendor_dlkm"]
    for name in logical:
        source = (args.vendor_image if name == "vendor" and args.vendor_image else
                  images / (name + ".img")).resolve(strict=True)
        assert source.is_file(), source
        dest = out / (name + ".img")
        if dest.is_symlink():
            dest.unlink()
        shutil.copy2(source, dest)
    for name in ("boot", "init_boot"):
        shutil.copy2(images / (name + ".img"), out / (name + ".img"))
    if args.kernel_image:
        kernel = args.kernel_image.resolve(strict=True)
        with kernel.open("rb") as source:
            assert source.read(64)[56:60] == b"ARMd", "Expected an uncompressed ARM64 Image"
        boot_unpack = out / "boot-unpacked"
        result = run([sys.executable, mkboot / "unpack_bootimg.py", "--boot_img",
                      images / "boot.img", "--out", boot_unpack,
                      "--format", "mkbootimg"], capture_output=True, text=True)
        boot_parameters = shlex.split(result.stdout)
        assert boot_parameters.count("--kernel") == 1
        boot_parameters[boot_parameters.index("--kernel") + 1] = str(kernel)
        run([sys.executable, mkboot / "mkbootimg.py", *boot_parameters,
             "--output", out / "boot.img"])
        run(avb + ["add_hash_footer", "--image", out / "boot.img",
                   "--partition_name", "boot", "--partition_size",
                   str((images / "boot.img").stat().st_size)])
    unpack = out / "unpacked"
    result = run([sys.executable, mkboot / "unpack_bootimg.py", "--boot_img",
                  args.previous / "vendor_boot.img", "--out", unpack,
                  "--format", "mkbootimg"], capture_output=True, text=True)
    parameters = shlex.split(result.stdout)
    cpio = rename_round((args.previous / "vendor.cpio").read_bytes(),
                        f"pixelos-round{args.round}",
                        args.first_stage_script.read_bytes().replace(b"\r\n", b"\n"))
    if args.init_rc:
        assert args.init_rc.startswith("/metadata/bootdiag/")
        assert "\n" not in args.init_rc and " " not in args.init_rc
        assert "--vendor_bootconfig" in parameters
        config = unpack / "bootconfig"
        lines = config.read_text().splitlines()
        init_rc = [i for i, line in enumerate(lines)
                   if line.startswith("androidboot.init_rc=")]
        assert len(init_rc) <= 1
        entry = "androidboot.init_rc=" + args.init_rc
        if init_rc:
            lines[init_rc[0]] = entry
        else:
            lines.append(entry)
        config.write_text("\n".join(lines).rstrip() + "\n")
    (out / "vendor.cpio").write_bytes(cpio)
    ramdisk = unpack / "vendor_ramdisk00"
    run([aosp / "out/host/linux-x86/bin/lz4", "-l", "-12", "-f",
         out / "vendor.cpio", ramdisk], stdout=subprocess.DEVNULL)
    run([sys.executable, mkboot / "mkbootimg.py", *parameters,
         "--vendor_boot", out / "vendor_boot.img"])
    run(avb + ["add_hash_footer", "--image", out / "vendor_boot.img",
               "--partition_name", "vendor_boot", "--partition_size", "100663296",
               "--algorithm", "SHA256_RSA4096", "--key", keys / "testkey_rsa4096.pem"])
    run(avb + ["extract_public_key", "--key", keys / "testkey_rsa2048.pem",
               "--output", out / "system.avbpubkey"])
    system_args = []
    for name in ("system", "system_ext", "product"):
        system_args += ["--include_descriptors_from_image", out / (name + ".img")]
    run(avb + ["make_vbmeta_image", "--output", out / "vbmeta_system.img",
               "--algorithm", "SHA256_RSA2048", "--key", keys / "testkey_rsa2048.pem",
               "--rollback_index", "1764892800", "--padding_size", "65536", *system_args])
    top_args = []
    for name in ("boot", "init_boot", "vendor_boot", "vendor", "odm", "system_dlkm", "vendor_dlkm"):
        top_args += ["--include_descriptors_from_image", out / (name + ".img")]
    run(avb + ["make_vbmeta_image", "--output", out / "vbmeta.img",
               "--algorithm", "SHA256_RSA4096", "--key", keys / "testkey_rsa4096.pem",
               "--flags", "3", "--padding_size", "65536", "--chain_partition",
               f"vbmeta_system:2:{out / 'system.avbpubkey'}", *top_args])
    with (out / "verify-avb.log").open("w") as log:
        run(avb + ["verify_image", "--image", out / "vbmeta.img",
                   "--follow_chain_partitions"], stdout=log, stderr=subprocess.STDOUT)
    manifest = []
    for path in sorted(out.glob("*.img")):
        sha = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                sha.update(chunk)
        manifest.append({"name": path.name, "size": path.stat().st_size,
                         "sha256": sha.hexdigest()})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Verified candidate:", out)


if __name__ == "__main__":
    main()
