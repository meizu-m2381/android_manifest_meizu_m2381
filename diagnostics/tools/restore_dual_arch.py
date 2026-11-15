"""Restore the secondary ABI required by the stock m2381 vendor services.

Save originals before editing both the local tree and the separate WSL tree.
"""

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    device = args.tree / "device/meizu/m2381"
    args.backup.mkdir(parents=True, exist_ok=True)
    for name in ("BoardConfig.mk", "custom_m2381.mk", "lineage_m2381.mk"):
        path = device / name
        original = path.read_text()
        if name == "BoardConfig.mk":
            if "TARGET_2ND_ARCH :=" in original:
                continue
            anchor = "TARGET_CPU_VARIANT_RUNTIME := kryo300\n"
            assert original.count(anchor) == 1
            new = original.replace(anchor, anchor + "\n"
                "# 原厂 OMX/CAS/外置相机 HAL 为 32 位，必须提供对应 linker 与基础库。\n"
                "TARGET_2ND_ARCH := arm\n"
                "TARGET_2ND_ARCH_VARIANT := armv8-2a\n"
                "TARGET_2ND_CPU_ABI := armeabi-v7a\n"
                "TARGET_2ND_CPU_ABI2 := armeabi\n"
                "TARGET_2ND_CPU_VARIANT := cortex-a55\n")
        else:
            full = "$(call inherit-product, build/make/target/product/full_base_telephony.mk)\n"
            core = "$(call inherit-product, build/make/target/product/core_64_bit.mk)\n"
            if core + full in original:
                continue
            assert full + core in original
            new = original.replace(full + core, core + full)
        saved = args.backup / name
        if not saved.exists():
            shutil.copy2(path, saved)
        path.write_text(new)
        print("updated", path)


if __name__ == "__main__":
    main()
