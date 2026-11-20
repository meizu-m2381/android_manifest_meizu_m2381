# Android 17 设备适配与平台隔离

M2381 的兼容处理位于设备/vendor 配置和独立二进制副本中，不修改公共 AOSP、冻结 VNDK 或 ROM 相机应用源码。

## 上游依据

采用 LineageOS 官方已有接口：

| 问题 | 官方实现 | 本设备的接入 |
| --- | --- | --- |
| 旧 `Trim` 签名 | [421619](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/421619) | 使用现有 `libbase_shim` |
| 旧 `Basename` / `Dirname` 签名 | [465067](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465067) | 使用同一官方 shim |
| 旧 `WriteStringToFd` 签名 | [465271](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465271) | 使用同一官方 shim |
| DPM 旧 `Parcel::setData` | [401141](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/401141) | 64 位官方 `libhidlbase_shim` 和独立 DPM 兼容副本 |
| SM8550 blob 接入 shim | [472159](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/472159)、[官方提取配置](https://github.com/LineageOS/android_device_xiaomi_sm8550-common/blob/lineage-23.2/extract-files.py) | `patchelf --add-needed libbase_shim.so` |
| 另一种旧 ABI 方案 | [465028](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/465028) | 上游使用 `replace_needed` 改为 `libbase-v33.so`；本设备不需要替换整份 libbase |
| 预编译内核头接口 | [427578](https://review.lineageos.org/c/LineageOS/android_vendor_lineage/+/427578)、[490401](https://review.lineageos.org/c/LineageOS/android_build_soong/+/490401) | `TARGET_PREBUILT_KERNEL_HEADERS`，保留通用生成器 |

二进制 patch 在这里修改 ELF 的依赖表，让动态链接器加载真实兼容实现。旧 `std::string` 引用和新 `std::string_view` 参数的调用约定不同，不能只把符号字符串改名当成 ABI 适配；也不使用空函数冒充实现。

## 设备专属输入和配置

`device/meizu/m2381/configs/compat/libbase-fixups.json` 固定 18 个实际打包的原厂 ELF 的原始摘要、修补摘要和旧符号。`tools/configure_blob_compat.py` 使用随源码提供的 `patchelf-0_17_2` 生成 `vendor/meizu/m2381/compat/vendor/...`，只切换对应安装规则。原始 `proprietary/` 不改写。工具先检查全组输入和已有输出；未知输入、输出冲突或规则重叠均停止。已记录摘要的旧兼容副本可以用 `--apply` 升级，检查模式拒绝未升级副本。32/64 位官方 libbase/libui shim 和 64 位官方 libhidlbase shim 由设备产品显式选择。

源码构建的 vendor libbinder 依赖系统 `libapexsupport.so`。设备用 `PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS` 的 `requireLibs` 配置 linker 可达性，不修改冻结的 VNDK33 清单。

`PRODUCT_SOURCE_ROOT_DIRS` 的负路径只在 M2381 产品中排除 stock HAL 对应的 Soong 定义。local manifest 不再移除 CAF display、audio、STHAL、IPA 项目，其他产品可以在同一 checkout 中使用这些源码。`core-utils-vendor/fwk-detect` 同样仅在本产品中排除，以保留原厂库及 CneApp 链接。它不是对其他设备构建成功的替代验证。

恢复完整源码项目后，Make 暴露了设备自定义 RFS 软链接与 `hardware/qcom-caf/common` 的 24 处重复安装定义。现改为引用上游同路径、同目标的模块，不再重复声明。

内核仓的 `kernel-headers.tar.gz` 是有限的编译兼容输入，包含已有 `msm_audio.h` 和上游清理工具要求的三个通用头。可用 `tools/package_build_headers.py --aosp AOSP_ROOT` 复现。它不是完整的原厂 UAPI，不能据此启用源码 QTI 音频/显示 HAL。上游头依赖选择器读取 shell 环境，因此构建入口在 lunch 后从实际 BoardConfig 导出该变量。

手动构建也需使用上游头选择接口；变量只传给这次构建，避免切换其他产品后残留设备头路径：

```bash
source build/envsetup.sh
lunch custom_m2381-cp2a-userdebug
TARGET_PREBUILT_KERNEL_HEADERS="$(get_build_var TARGET_PREBUILT_KERNEL_HEADERS)" m pixelos -j12
```


## 媒体与运行时依赖

产品选择上游 `libprocessgroup.vendor:64`，避免 qguard 通过 VNDK33 namespace
加载旧 libprocessgroup 后无法解析旧 `WriteStringToFd`。

32 位原厂 codec2 的 helper 依赖改为单独命名的
`libstagefright_bufferqueue_helper-v33.so`，从冻结 API33 输入生成副本并固定摘要；
另添加官方 `libui_shim.so` 兼容旧 mapper 调用。依据为 LineageOS
[394610](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/394610)、
[394611](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/394611)；
保留旧库并改 SONAME 的先例见
[410069](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/410069)。
冻结 APEX 输入不改写。

相机/音频 HAL 还通过 dlopen 加载回溯库。产品显式打包两种架构的
`libutilscallstack.vendor` 与 `libunwindstack.vendor`，避免落入旧 VNDK33
回溯链后缺失 `Basename`。单靠 DT_NEEDED 符号集合检查无法覆盖这条路径。

## 验证边界

兼容回归覆盖兼容副本升级、未知输入拒绝与 helper 复现。实际构建和真机加载已验证上述兼容依赖；
修复后的定向镜像已启动，并完成三摄拍照、音视频采集和硬件解码检查。
这次镜像验证使用安装目录重打包，不能代替全新同步后的完整源码构建或通用 OTA 验证。

Aperture 的 60 FPS 档位由设备 RRO 的 `config_additionalVideoConfigurations`
为相机 ID 0/1/3 添加。Camera2 三摄各 720p/1080p/4K 九组短录像实测约
59–60 / 59–60 / 58 fps，传感器间隔约 16.67 ms；用户确认相机应用出现档位。
尚未统计 Aperture 自身录像的逐帧输出，也未验证长时间热稳定录像。

标准启动已去除诊断依赖，SELinux 仍为 permissive；Recovery/OTA 与其他待办见
[功能状态](status.md)。
