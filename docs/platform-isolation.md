# Android 17 设备适配与平台隔离

当前迁移将 M2381 的兼容处理留在设备/vendor 仓库，不再要求六项 Android 17 平台补丁。历史补丁保留用于识别和撤销已有工作区；不能再用 `--apply` 重新应用 Android 17 补丁。

## 上游依据

先对照 LineageOS 官方提交及 WSL 当前源码，采用已有接口：

| 问题 | 官方实现 | 本设备的接入 |
| --- | --- | --- |
| 旧 `Trim` 签名 | [421619](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/421619) | 使用现有 `libbase_shim` |
| 旧 `Basename` / `Dirname` 签名 | [465067](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465067) | 使用同一官方 shim |
| 旧 `WriteStringToFd` 签名 | [465271](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465271) | 使用同一官方 shim |
| SM8550 blob 接入 shim | [472159](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/472159)、[官方提取配置](https://github.com/LineageOS/android_device_xiaomi_sm8550-common/blob/lineage-23.2/extract-files.py) | `patchelf --add-needed libbase_shim.so` |
| 另一种旧 ABI 方案 | [465028](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/465028) | 上游使用 `replace_needed` 改为 `libbase-v33.so`；本设备不需要替换整份 libbase |
| 预编译内核头接口 | [427578](https://review.lineageos.org/c/LineageOS/android_vendor_lineage/+/427578)、[490401](https://review.lineageos.org/c/LineageOS/android_build_soong/+/490401) | `TARGET_PREBUILT_KERNEL_HEADERS`，保留通用生成器 |

二进制 patch 在这里修改 ELF 的依赖表，让动态链接器加载真实兼容实现。旧 `std::string` 引用和新 `std::string_view` 参数的调用约定不同，不能只把符号字符串改名当成 ABI 适配；也不使用空函数冒充实现。

## 设备专属输入和配置

`device/meizu/m2381/configs/compat/libbase-fixups.json` 固定 13 个实际打包的原厂 ELF 的原始摘要、修补摘要和旧符号。`tools/configure_blob_compat.py` 使用随源码提供的 `patchelf-0_17_2` 生成 `vendor/meizu/m2381/compat/vendor/...`，只切换对应安装规则。原始 `proprietary/` 不改写。工具先检查全组输入和已有输出；未知输入、输出冲突或规则重叠均停止。32/64 位官方 shim 由设备产品显式选择。

原 VNDK33 LLNDK 清单补丁源于源码构建的 **vendor libbinder** 依赖当前系统 `libapexsupport.so`。当前 VNDK33 快照中的 libbinder 不含该依赖。设备改用 `PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS` 的 `requireLibs`，不修改冻结的 VNDK33 清单；需校验最终 linker 配置与依赖可达性。

`PRODUCT_SOURCE_ROOT_DIRS` 的负路径只在 M2381 产品中排除 stock HAL 对应的 Soong 定义。local manifest 不再移除 CAF display、audio、STHAL、IPA 项目，其他产品可以在同一 checkout 中使用这些源码。`core-utils-vendor/fwk-detect` 同样仅在本产品中排除，以保留原厂库及 CneApp 链接。它不是对其他设备构建成功的替代验证。

恢复完整源码项目后，Make 暴露了设备自定义 RFS 软链接与 `hardware/qcom-caf/common` 的 24 处重复安装定义。现改为引用上游同路径、同目标的模块，不再重复声明。

内核仓的 `kernel-headers.tar.gz` 是有限的编译兼容输入，包含已有 `msm_audio.h` 和上游清理工具要求的三个通用头。可用 `tools/package_build_headers.py --aosp AOSP_ROOT` 复现。它不是完整的原厂 UAPI，不能据此启用源码 QTI 音频/显示 HAL。上游头依赖选择器读取 shell 环境，因此构建入口在 lunch 后从实际 BoardConfig 导出该变量。

## 从旧工作区迁移

先审阅和提交已有更改，保存可回退点；不要混入临时镜像或日志。同步三个 split 仓库与本 manifest 工具仓后：

```bash
android_root=/path/to/android
port_root=/path/to/android_manifest_meizu_m2381
cp "$port_root"/local_manifests/*.xml "$android_root/.repo/local_manifests/"
cd "$android_root"
repo sync -c -j4 --no-clone-bundle --no-tags
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --restore
python3 device/meizu/m2381/tools/configure_blob_compat.py --aosp "$android_root" --apply
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --require-unpatched
bash "$port_root/scripts/build-pixelos.sh" "$android_root" 12
```

新同步的已打包 vendor 仓库包含兼容副本，`--apply` 可重复执行。恢复器仅识别记录的 before/after 摘要；其他本地改动必须人工审阅，不能强制覆盖。它恢复文件内容，不删除历史提交。

手动构建也需使用上游头选择接口；变量只传给这次构建，避免切换其他产品后残留设备头路径：

```bash
source build/envsetup.sh
lunch custom_m2381-cp2a-userdebug
TARGET_PREBUILT_KERNEL_HEADERS="$(get_build_var TARGET_PREBUILT_KERNEL_HEADERS)" m pixelos -j12
```

主机内存补丁已退出必需项。原 `env -i` 会清除外壳的 Go 内存参数；只在外壳 export 不代表 Soong runtime 已收到。本轮有限内存验证直接给构建生成的 `soong_build` 命令传入 `GOMEMLIMIT=32GiB GOGC=30`。整条构建流水线另使用仅位于 `out` 的临时 host 启动包装，向同一原版 ELF 传参，验证后恢复两个生成工具路径；不改 AOSP 源码或原版 ELF 内容。充足内存的常规构建不需要这个操作。

本轮构建、静态 ELF、失败保护和源码恢复证据见后续验证记录；构建通过不等于已刷机或全部硬件回归通过。当前 Android 16 补丁仅作历史归档，尚未按此方案重验。

## 2026-11-16 验证结果

本轮以 WSL `/home/zhaiy/pixelos17` 的 Android 17 checkout 验证，设备、内核和 vendor 的 Windows 提交分别为 `3d62681`、`f4670f8`、`fdc958b`。WSL 对应提交为 `36aec52`、`1bf5c59`、`b60fc2e`；提交信息不同，适配文件内容一致。

| 验证 | 结果与边界 |
| --- | --- |
| 平台还原 | 六个记录文件均符合 before SHA-256；四个平台仓库恢复提交为 libbase `360ce34`、VNDK33 `e9c3e23`、Lineage `d24a238`、Soong `5c82054` |
| 迁移及失败保护 | 7 项测试通过，包括真实六项旧补丁还原、13 个真实 blob 重复修补、未知输入及输出冲突时不写入 |
| 安装规则 | 5418 个本地输入、2924 个库路径检查通过；77 条复制规则无 blob 目标冲突；生成的 Soong 安装清单没有重复目标 |
| 产品隔离 | 恢复 manifest 中原排除的 10 个项目；M2381 完整 Soong 分析与 Make 规则生成通过；`aosp_arm64` dumpvars 中设备源码过滤、设备 namespace 和预编译头变量为空 |
| 实际目标构建 | 从已生成的产品图通过 Ninja 续编，退出码 0；未跳过编译动作，但复用了已生成的产品构建图，未重新执行 lunch/Soong 分析 |
| 内核头 | 未修改的上游 `prebuilt_kernel_includes` 实际生成 `msm_audio.h`，内容与输入相同；归档可逐字节复现 |
| ELF 安装产物 | 13 个实际安装 blob 全部匹配修补后摘要；32/64 位官方 shim 均已安装；当前 vendor 中 156 个引用 libbase 的 ELF 没有缺失的 `android::base` 强引用符号 |
| 排除残留补丁 | 两种架构所需的三个旧签名在当前 libbase 中缺失，均由官方 shim 导出；因此符号检查不依赖历史 libbase 补丁 |
| VNDK33 | 重新构建并提取真实安装的 VNDK33 APEX，LLNDK 清单没有添加 `libapexsupport.so`；快照 libbinder 不依赖它，源码 vendor libbinder 依赖它 |
| linker 对照 | 从 41 个实际安装 APEX 提取 host 验证根目录，普通模式生成配置成功；设备 fragment 让 `[vendor]` 的 default、`[system]` 和 `[unrestricted]` 的 sphal 链接到系统 libapexsupport；去掉 fragment 后这些链接全部消失 |

实际构建目标包括 `libbase_shim`、`libtinycompress`、`android.hardware.boot-service.qti`、`prebuilt_kernel_headers`、host `linkerconfig`、两种架构的 vendor libbase/libbinder、13 个兼容 blob、vendor linker protobuf、`llndk.libraries.33.txt` 及 `com.android.vndk.v33`。主机的两个 Soong 工具路径已恢复为原版 ELF，七个相关 WSL Git 仓库干净。

保留在 WSL `out/` 的证据：

- `m2381-no-platform-resume.log`：成功续编日志。
- `m2381-no-platform-libbase-abi.json`：156 个引用 ELF 的符号审计。
- `m2381-no-platform-validation.json`：本轮结果及验证边界。
- `m2381-no-platform-linkerconfig/ld.config.txt` 与 `m2381-no-platform-linkerconfig-control/ld.config.txt`：有/无设备 fragment 的实际生成配置。
- `m2381-no-platform-revisions.xml`：本轮源码版本清单。

全根目录的 host `--strict` 检查仍被现有 system 配置的 `libdexfiled.so` 需求拦住；普通模式同时提示缺少 `system/etc/vndkcorevariant.libraries.txt`。上述 linker 结果只证明本设备新增依赖的配置可达性，不表示整棵暂存根目录已通过严格依赖校验。未构建全量 OTA，也未进行刷机、启动或硬件回归。

Make 仍有历史 blob 对源码安装规则的覆盖警告，包括 libtinycompress；本轮修复的是恢复公共项目后出现的重复软链接，不能把它等同于全部历史安装归属已清理。
