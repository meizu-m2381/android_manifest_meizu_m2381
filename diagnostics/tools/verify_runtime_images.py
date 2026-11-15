"""Verify actual m2381 image contents before another boot attempt.

Checks filesystem extraction, split policy compilation, runtime architectures,
source tool ownership and retained vendor libbase symbol compatibility.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

from audit_vendor_libbase_abi import symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    aosp = args.aosp.resolve()
    images = aosp / "out/target/product/m2381"
    host = aosp / "out/host/linux-x86/bin"
    tools = Path(__file__).resolve().parent
    parts = ["system", "system_ext", "product", "vendor", "odm", "system_dlkm", "vendor_dlkm"]

    def run(command, **kwargs):
        return subprocess.run(list(map(str, command)), check=True, **kwargs)

    def extract(part):
        with (out / (part + ".log")).open("w") as log:
            run([host / "fsck.erofs", "--extract=" + str(out / part),
                 images / (part + ".img")], stdout=log, stderr=subprocess.STDOUT)
        return part

    with ThreadPoolExecutor(max_workers=3) as pool:
        for part in pool.map(extract, parts):
            print("EROFS verified:", part, flush=True)
    system = out / "system/system"
    if not system.is_dir():
        system = out / "system"
    vendor = out / "vendor"
    for name, target in {"getprop": "toolbox", "modprobe": "toolbox",
                         "setprop": "toolbox", "sed": "toybox_vendor",
                         "sort": "toybox_vendor", "grep": "toybox_vendor"}.items():
        path = vendor / "bin" / name
        assert path.is_symlink() and path.readlink() == Path(target), (name, path)
    for name in ("toolbox", "toybox_vendor", "boringssl_self_test32", "boringssl_self_test64"):
        path = vendor / "bin" / name
        assert path.stat().st_mode & 0o111, path
    for bits, name in ((1, "boringssl_self_test32"), (2, "boringssl_self_test64")):
        assert symbols(vendor / "bin" / name)[0] == bits
    rc = vendor / "etc/init/boringssl_self_test.rc"
    assert rc.read_bytes() == (aosp / "external/boringssl/selftest/boringssl_self_test.rc").read_bytes()
    props = dict(line.split("=", 1) for line in (vendor / "build.prop").read_text().splitlines()
                 if "=" in line and not line.startswith("#"))
    assert props["ro.zygote"] == "zygote64_32"
    assert props["ro.vndk.version"] == "33"
    assert "armeabi-v7a" in props["ro.vendor.product.cpu.abilist32"]
    assert props["ro.vendor.product.cpu.abilist64"] == "arm64-v8a"
    for name in ("linker", "linker64"):
        path = system / "bin" / name
        assert path.is_symlink() and str(path.readlink()) == "/apex/com.android.runtime/bin/" + name

    deapex = [host / "deapexer", "--debugfs_path", host / "debugfs_static",
              "--fsckerofs_path", host / "fsck.erofs", "list"]
    for name, apex, entries in [
        ("runtime", system / "apex/com.android.runtime.apex",
         ["bin/linker", "bin/linker64", "lib/bionic/libc.so", "lib64/bionic/libc.so"]),
        ("vndk33", out / "system_ext/apex/com.android.vndk.v33.apex",
         ["lib/libbinder.so", "lib64/libbinder.so", "lib/libutils.so", "lib64/libutils.so"]),
    ]:
        listing = run(deapex + [apex], capture_output=True, text=True).stdout
        (out / (name + "-contents.txt")).write_text(listing)
        listed = {line.removeprefix("./") for line in listing.splitlines()}
        assert set(entries) <= listed, (name, set(entries) - listed)
        print("APEX architectures verified:", name, flush=True)
    run([sys.executable, tools / "audit_vendor_libbase_abi.py", vendor,
         "--report", out / "libbase-abi.json"])
    run([sys.executable, tools / "check_split_policy.py", "--secilc", host / "secilc",
         "--system", system, "--system-ext", out / "system_ext",
         "--product", out / "product", "--vendor", vendor, "--odm", out / "odm",
         "--output", out / "policy"])
    count = len(list((out / "vendor_dlkm/lib/modules").rglob("*.ko")))
    assert count == 304, count
    (out / "verified.json").write_text(json.dumps({
        "erofs": parts, "runtime_abis": ["arm", "arm64"], "vndk": 33,
        "source_tools": True, "vendor_libbase_abi": True,
        "split_policy": True, "vendor_dlkm_modules": count,
    }, indent=2) + "\n")
    print("Actual image verification passed:", out, flush=True)


if __name__ == "__main__":
    main()
