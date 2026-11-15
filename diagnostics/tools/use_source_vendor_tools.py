"""Replace imported platform multicall tools and BoringSSL tests with source modules.

The blob generator expands symlinks into files, so aliases must be removed by
content, not merely by their toolbox/toybox names. Preserve original files in
the specified backup directory and leave proprietary binaries untouched.
"""

import argparse
import hashlib
import re
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--aosp", type=Path, required=True)
    args = parser.parse_args()
    vendor = args.tree / "vendor/meizu/m2381"
    blobs = vendor / "proprietary/vendor"
    digest = lambda p: hashlib.sha256(p.read_bytes()).digest()
    tools = {digest(blobs / "bin/toolbox"), digest(blobs / "bin/toybox_vendor")}
    paths = {
        "vendor/" + p.relative_to(blobs).as_posix()
        for p in (blobs / "bin").iterdir()
        if p.is_file() and digest(p) in tools
    }
    paths.update({"vendor/bin/boringssl_self_test32",
                  "vendor/bin/boringssl_self_test64",
                  "vendor/etc/init/boringssl_self_test.rc"})
    source_binaries = {"sh", "awk", "dumpsys", "vndservice", "vndservicemanager",
                       "logwrapper", "checkpoint_gc", "system_dlkm_modprobe.sh",
                       "vendor_modprobe.sh"}
    paths.update("vendor/bin/" + name for name in source_binaries)
    # Confirm all former command aliases are supplied by the new multicall tools.
    bp = (args.aosp / "external/toybox/Android.bp").read_text()
    toy_aliases = set(re.findall(r'"([^"\n]+)"',
        re.search(r"toybox_symlinks = \[(.*?)\n\]", bp, re.S).group(1)))
    supplied = toy_aliases | source_binaries | {"toolbox", "toybox_vendor", "getevent", "getprop",
                              "modprobe", "setprop", "start", "stop"}
    missing = {Path(p).name for p in paths if p.startswith("vendor/bin/")
               and "boringssl" not in p} - supplied
    assert not missing, f"Unprovided command aliases: {sorted(missing)}"
    mk_path = vendor / "Android.mk"
    original = mk_path.read_text()
    chunks = re.split(r"(?=include \$\(CLEAR_VARS\)\n)", original)
    kept, removed = [], set()
    for chunk in chunks:
        src = re.search(r"^LOCAL_SRC_FILES := proprietary/(.+)$", chunk, re.M)
        if src and src.group(1) in paths:
            removed.add(re.search(r"^LOCAL_MODULE := (.+)$", chunk, re.M).group(1))
        else:
            kept.append(chunk)
    changes = {mk_path: "".join(kept)}
    product = vendor / "m2381-vendor.mk"
    changes[product] = "".join(line for line in product.read_text().splitlines(True)
                               if line.strip().removesuffix("\\").strip() not in removed)
    proprietary = args.tree / "device/meizu/m2381/proprietary-files.txt"
    if proprietary.exists():
        changes[proprietary] = "".join(
            line for line in proprietary.read_text().splitlines(True)
            if line.strip().lstrip("-").split(";", 1)[0] not in paths)
    excludes = args.tree / "tools/blob_exclude.txt"
    if excludes.exists():
        old = excludes.read_text()
        existing = {line.strip() for line in old.splitlines()}
        additional = sorted(paths - existing)
        changes[excludes] = old + ("\n# 通用运行时工具由当前 PixelOS 源码构建，禁止导入旧版别名。\n"
                                   + "\n".join(additional) + "\n" if additional else "")
    device = args.tree / "device/meizu/m2381/device.mk"
    old = device.read_text()
    packages = ("# 通用工具必须与当前 vendor 运行库一起构建。\n"
                "PRODUCT_PACKAGES += \\\n"
                "    toolbox_vendor \\\n"
                "    toybox_vendor \\\n"
                "    boringssl_self_test_vendor\n\n")
    if "# 通用工具必须与当前 vendor 运行库一起构建。" not in old:
        anchor = "# Fastbootd\n"
        assert old.count(anchor) == 1
        changes[device] = old.replace(anchor, packages + anchor)
    old = changes.get(device, old)
    if "    sh_vendor \\\n" not in old:
        changes[device] = old.replace("    boringssl_self_test_vendor\n",
            "    boringssl_self_test_vendor \\\n"
            "    sh_vendor \\\n"
            "    awk_vendor \\\n"
            "    dumpsys_vendor \\\n"
            "    vndservice \\\n"
            "    vndservicemanager \\\n"
            "    logwrapper_vendor\n")
    old = changes.get(device, old)
    if "    ro.vndk.version=33\n" not in old:
        anchor = "PRODUCT_EXTRA_VNDK_VERSIONS := 33\n"
        assert old.count(anchor) == 1
        changes[device] = old.replace(anchor, anchor + "\n"
            "# 原厂 vendor API 33；仅安装 APEX 不会启用对应的 linker 命名空间。\n"
            "PRODUCT_VENDOR_PROPERTIES += \\\n"
            "    ro.vndk.version=33\n")
    for path, new in changes.items():
        if path.read_text() == new:
            continue
        saved = args.backup / path.relative_to(args.tree)
        saved.parent.mkdir(parents=True, exist_ok=True)
        if not saved.exists():
            shutil.copy2(path, saved)
        path.write_text(new)
        print("updated", path.relative_to(args.tree))
    print("source-provided paths:", len(paths), "removed blob modules:", len(removed))


if __name__ == "__main__":
    main()
