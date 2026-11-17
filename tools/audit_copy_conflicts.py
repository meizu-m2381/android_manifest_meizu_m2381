"""检测 PRODUCT_COPY_FILES 与已选中的 vendor 预编译模块的安装路径冲突。

仅保留在 proprietary 中的文件不代表会安装；以生成的模块及产品包清单为准。
"""

import os
import re

DEVICE_MK = 'device/meizu/m2381/device.mk'
VENDOR_MK = 'vendor/meizu/m2381/Android.mk'
PRODUCT_MK = 'vendor/meizu/m2381/m2381-vendor.mk'

DEST_MAP = {
    '$(TARGET_COPY_OUT_VENDOR)': 'vendor',
    '$(TARGET_COPY_OUT_ODM)': 'odm',
    '$(TARGET_COPY_OUT_SYSTEM)': 'system',
    '$(TARGET_COPY_OUT_SYSTEM_EXT)': 'system_ext',
    '$(TARGET_COPY_OUT_PRODUCT)': 'product',
    '$(TARGET_COPY_OUT_VENDOR_DLKM)': 'vendor_dlkm',
    '$(TARGET_COPY_OUT_SYSTEM_DLKM)': 'system_dlkm',
}


def parse_copies():
    s = open(DEVICE_MK, encoding='utf-8').read()
    # 去掉换行续行
    s = s.replace('\\\n', ' ')
    pairs = []
    for line in s.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        for token in line.split():
            if token.count(':') == 1 and ('COPY_OUT' in token):
                src, dst = token.split(':', 1)
                pairs.append((src, dst))
    return pairs


def resolve(dst):
    for var, root in DEST_MAP.items():
        if dst.startswith(var + '/'):
            return root + '/' + dst[len(var) + 1:]
    return None


def installed_blobs():
    with open(PRODUCT_MK, encoding='utf-8') as f:
        packages = set(re.sub(r'#.*', '', f.read()).replace('\\\n', ' ').split())
    with open(VENDOR_MK, encoding='utf-8') as f:
        blocks = f.read().split('include $(CLEAR_VARS)')
    destinations = set()
    for block in blocks:
        def field(name):
            match = re.search(r'^' + name + r'\s*:=\s*(.*?)\s*$', block, re.M)
            return match[1] if match else None
        if field('LOCAL_MODULE') not in packages:
            continue
        path, stem = field('LOCAL_MODULE_PATH'), field('LOCAL_MODULE_STEM')
        if not path or not stem:
            continue
        for root in ('vendor', 'odm', 'vendor_dlkm', 'system_dlkm'):
            prefix = '$(TARGET_OUT_' + root.upper() + ')'
            if path == prefix or path.startswith(prefix + '/'):
                destinations.add(root + path[len(prefix):] + '/' + stem)
                break
    return destinations


def main():
    pairs = parse_copies()
    installed = installed_blobs()
    print('PRODUCT_COPY_FILES 条目:', len(pairs))
    dup = []
    missing_src = []
    for src, dst in pairs:
        real = resolve(dst)
        if not real:
            continue
        for root in ('vendor', 'odm', 'vendor_dlkm', 'system_dlkm'):
            if real.startswith(root + '/'):
                if real in installed:
                    dup.append((src, real))
                break
        if src.startswith('$(LOCAL_PATH)/'):
            sp = os.path.join('device/meizu/m2381', src[len('$(LOCAL_PATH)/'):])
            if not os.path.exists(sp):
                missing_src.append(src)

    print('与 blobs 目标冲突:', len(dup))
    for src, real in dup:
        print('  冲突:', real, '  <-- ', src)
    if missing_src:
        print('源文件缺失:', len(missing_src))
        for m in missing_src:
            print('  缺:', m)

    raise SystemExit(bool(dup or missing_src))


if __name__ == '__main__':
    main()
