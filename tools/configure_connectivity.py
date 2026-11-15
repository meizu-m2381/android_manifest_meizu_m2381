"""Remove imported Wi-Fi services which override the source-built AIDL stack.

Keep the original extracted files locally; only remove their generated install
rules. blob_exclude.txt applies the same ownership rules to future extraction.
"""

import argparse
import re
from pathlib import Path


SOURCE_OWNED = {
    "vendor/bin/hw/android.hardware.wifi@1.0-service",
    "vendor/etc/init/android.hardware.wifi@1.0-service.rc",
    "vendor/etc/vintf/manifest/android.hardware.wifi@1.0-service.xml",
    "vendor/lib64/libwifi-hal.so",
    "vendor/bin/hw/wpa_supplicant",
    "vendor/etc/init/android.hardware.wifi.supplicant-service.rc",
    "vendor/etc/vintf/manifest/android.hardware.wifi.supplicant.xml",
    "vendor/bin/hw/hostapd",
    "vendor/etc/init/hostapd.android.rc",
    "vendor/etc/vintf/manifest/android.hardware.wifi.hostapd.xml",
    "vendor/etc/init/ssgtzd.rc",
    "vendor/overlay/WifiResCommon_Vendor_Mz.apk",
}


def configure(tree, source_owned=SOURCE_OWNED):
    vendor = tree / "vendor/meizu/m2381"
    makefile = vendor / "Android.mk"
    text = makefile.read_text(encoding="utf-8")
    removed = set()

    def replace(match):
        block = match.group(0)
        src = re.search(r"^LOCAL_SRC_FILES := proprietary/(.+)$", block, re.M)
        if src and src.group(1).strip() in source_owned:
            module = re.search(r"^LOCAL_MODULE := (.+)$", block, re.M)
            if module is None:
                raise ValueError("Missing module name in imported service rule")
            removed.add(module.group(1).strip())
            return ""
        return block

    updated = re.sub(
        r"include \$\(CLEAR_VARS\)\n.*?include \$\(BUILD_PREBUILT\)\n\n?",
        replace, text, flags=re.S,
    )
    changes = {makefile: updated}
    product = vendor / "m2381-vendor.mk"
    changes[product] = "".join(
        line for line in product.read_text(encoding="utf-8").splitlines(True)
        if line.strip().removesuffix("\\").strip() not in removed
    )
    manifest = tree / "device/meizu/m2381/proprietary-files.txt"
    changes[manifest] = "".join(
        line for line in manifest.read_text(encoding="utf-8").splitlines(True)
        if line.strip().lstrip("-").split(";", 1)[0] not in source_owned
    )
    for path, data in changes.items():
        if data != path.read_text(encoding="utf-8"):
            path.write_text(data, encoding="utf-8", newline="\n")
            print("updated", path.relative_to(tree))
    print("removed imported install rules:", len(removed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    configure(parser.parse_args().tree)
