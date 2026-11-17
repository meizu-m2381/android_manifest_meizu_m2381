# PixelOS 17 构建指南

当前使用 PixelOS `seventeen`、Android 17 与 LineageOS `lineage-24.0` 接口。
使用满足 PixelOS 上游要求的 Linux 环境、构建依赖、Git LFS 和磁盘空间。
本工具仓放在 Android 源码目录之外，避免辅助源码进入 Soong 扫描。

## 同步源码

在独立 Android 源码目录执行：

```bash
repo init -u https://github.com/PixelOS-AOSP/android_manifest.git \
  -b seventeen --depth=1 --manifest-depth=1 \
  --partial-clone --clone-filter=blob:none \
  --git-lfs --no-clone-bundle --no-tags --platform=linux
mkdir -p .repo/local_manifests
cp /path/to/android_manifest_meizu_m2381/local_manifests/*.xml .repo/local_manifests/
repo sync -c -j4 --no-clone-bundle --no-tags
```

三个项目分别同步到 `device/meizu/m2381`、`device/meizu/m2381-kernel`、
`vendor/meizu/m2381`，不再手工 rsync 覆盖。两个空兼容清单用于覆盖旧版本的
全局排除规则，不要复制历史清单恢复 `remove-project`。

浅历史和对象过滤仍需下载实际构建内容。保留 `.repo`；不要删除它来省空间，
也不要按本机内核版本删掉 Trusty/Microdroid 等上游依赖。
`repo sync` 后确认设备、内核、vendor 及 GMS 的 LFS 实体齐全；缺失时在对应仓库
执行 `git lfs pull`，不能将指针文件当作 APK、APEX 或驱动打包。

## 准备与构建

```bash
port_root=/path/to/android_manifest_meizu_m2381
android_root=/path/to/android
python3 "$port_root/tools/check_bundled_inputs.py" --root "$android_root"
bash "$port_root/scripts/build-pixelos.sh" "$android_root" 12
```

构建入口会核验充电兼容模块、固定输入、LFS 与设备 ELF 兼容副本，
读取上游 release 后选择 `custom_m2381-<release>-userdebug`。
它还在 lunch 后导出 `TARGET_PREBUILT_KERNEL_HEADERS` 并确认 ARM64 设备配置。
兼容输入缺失或与已知摘要不符时会停止；需要复现兼容副本时见
[修补说明](patches.md)，不要绕过摘要检查。

旧工作区需先保存本地更改，并对照上游撤销历史平台改动；也可在独立目录全新同步。
`repo sync` 不会自动撤销本地提交。有限内存环境需按上游实际构建进程排查内存占用，单纯 export
`GOMEMLIMIT` 不保证它能穿过构建器的 `env -i`。

## 版本记录与安装边界

保存本次构建的真实版本，而不是复用旧验证记录：

```bash
repo manifest -r -o revisions.xml
repo status
```

`provenance/pixelos17/revisions.xml` 是历史源码同步快照，不包含后续全部修复，
不是最终测试版本的锁定清单。当前远端 `main` 随提交变化，发布时应另存本次
源码版本及本工具仓提交。

现有手机仍使用匹配的诊断 ramdisk、bootconfig、模块、AVB 链和 metadata 入口。
默认 OTA 不会自动安装这些依赖；正式 recovery、去除诊断入口后的启动、OTA
及双槽升级尚未完成验证。当前仓库不提供通用的一键刷机流程，见
[功能状态](status.md)。
