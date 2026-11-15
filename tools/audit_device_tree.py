"""静态检查设备树与 vendor blobs 的模块一致性。

输出三类信息：
1. device.mk 里 PRODUCT_PACKAGES 引用了、但本地设备树没定义、vendor blobs 里也没有的包
   （这些要么来自 AOSP/Lineage 源码，要么是 21 Note 残留 —— 需要人工判断）
2. 设备树本地定义了但没被打包的模块（通常是死代码）
3. vendor blobs 模块名清单规模
"""

import os
import re

DEVICE = 'device/meizu/m2381'
VENDOR_MK = 'vendor/meizu/m2381/m2381-vendor.mk'


def collect_local_modules():
    names = set()
    for base, _, files in os.walk(DEVICE):
        for f in files:
            p = os.path.join(base, f)
            if f == 'Android.bp' or f.endswith('.bp'):
                s = open(p, encoding='utf-8', errors='ignore').read()
                names.update(re.findall(r'name:\s*"([^"]+)"', s))
            elif f == 'Android.mk' or f.endswith('.mk'):
                s = open(p, encoding='utf-8', errors='ignore').read()
                names.update(re.findall(r'LOCAL_MODULE\s*:=\s*(\S+)', s))
    return names


def collect_product_packages():
    names = []
    for f in ('device.mk', 'lineage_m2381.mk'):
        p = os.path.join(DEVICE, f)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8', errors='ignore').read()
        for block in re.findall(r'PRODUCT_PACKAGES\s*\+?=\s*\\?\n((?:[^\n]*\\\n)*[^\n]*)', s):
            for line in block.split('\n'):
                line = line.strip().rstrip('\\').strip()
                if line and not line.startswith('#'):
                    names.append(line)
        # 单行形式
        for m in re.findall(r'PRODUCT_PACKAGES\s*\+?=\s*([^\n\\]+)', s):
            names.extend(x.strip() for x in m.split() if x.strip())
    return sorted(set(names))


def collect_vendor_modules():
    if not os.path.exists(VENDOR_MK):
        return set()
    s = open(VENDOR_MK, encoding='utf-8', errors='ignore').read()
    return set(re.findall(r'^\s+(mz_\S+)\s*\\?$', s, re.M))


def main():
    local = collect_local_modules()
    pkgs = collect_product_packages()
    vendor = collect_vendor_modules()

    unknown = [p for p in pkgs if p not in local and p not in vendor]
    print('PRODUCT_PACKAGES 总数:', len(pkgs))
    print('本地定义模块:', len(local), ' vendor blobs 模块:', len(vendor))
    print()
    print('无法在本地/blobs 中找到的包（需人工判断是 AOSP 还是 21 Note 残留）:')
    for u in unknown:
        print('  ', u)


if __name__ == '__main__':
    main()
