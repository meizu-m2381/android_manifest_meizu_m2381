# 当前修改的范围

Android 17 使用独立的 `patches/platform-17-series.json`，Android 16 保留原补丁组。`apply_platform_patches.py` 按目标 PixelOS 版本选择；其他 ROM 可明确给出 `--series`。Android 17 当前仅完成补丁应用检查，升级验证见 `docs/upgrade-pixelos17.md`。

## 平台源码补丁

`patches/platform-series.json` 记录目标文件、前后 SHA-256、基线来源和可选标记。`apply_platform_patches.py` 先检查全组文件，拒绝未知摘要；默认只读，`--apply` 才写入，并保留原文件到目标 AOSP 的 `out/m2381-source-backups`。已修补文件可重复检查。

| 补丁 | 目的 |
| --- | --- |
| 0001 `system/libbase/strings.cpp` | 提供旧厂商库需要的非模板 Trim ABI |
| 0002 `system/libbase/file.cpp` | 兼容旧 WriteStringToFd 和 Basename 符号 |
| 0003/0004 VNDK33 arm/arm64 LLNDK 列表 | 补入 libapexsupport |
| 0005 Lineage `generated_kernel_includes` | 当前预编译内核阶段的历史编译头生成方式 |
| 0006 `build/soong/ui/build/soong.go` | 主机 Go 内存参数透传（GOMEMLIMIT / GOGC） |

Android 16 组另有可选的 TurboAdapter R8 规避，不自动应用。

不再需要的源码改动全部改由 `repo` 机制承担，见 `local_manifests/01-m2381-excluded-projects.xml`：

| 原改法 | 现做法 |
| --- | --- |
| 给 CAF display 加 `soong_namespace` 改动 | `remove-project` 移除 `hardware/qcom-caf/sm8550/display` |
| 给 `BoardConfigQcom.mk` 加机型特判 | 设备 `BoardConfig.mk` 设 `USE_DEVICE_SPECIFIC_DATA_IPA_CFG_MGR := true` |
| 构建前把音频/IPA 源码目录改名 | `remove-project` 移除 9 个 audio / STHAL / IPA 项目 |
| 改 `build-manifest_xml.mk` 生成规则 | 项目已不在 manifest 中，`repo manifest -r` 不再失败 |

`build/soong/ui/build/soong.go` 那条无法用环境变量替代：`build/blueprint/bootstrap/bootstrap.go:174` 以 `env -i $env "$BUILDER"` 启动 soong_build，外壳导出的 `GOMEMLIMIT` 不会传进去，必须在 `soong.go` 的 `invocationEnv` 里显式带出。它只影响主机侧解析内存，不改产品配置。

`nqnfcinfo` 是 `LineageOS/android_hardware_qcom-caf_common` 项目内的子目录，`remove-project` 管不到；它的模块不在 `PRODUCT_PACKAGES`，设备使用同名 blob，无需处理。

VNDK 基线来自修补前备份。libbase 与 TurboAdapter 基线由当前文件移除有记录的新增块重建；Lineage 头生成补丁的原始块参考 lineage-23.2，再嵌回当前文件。它们不是声称来自一个完整、已锁定的上游提交。部分补丁注释沿用历史措辞；实际头生成方式是编译阶段妥协，不代表所有内核 UAPI 都已提供。

## 厂商输入修正

- `patches/vendor-text-fixups.json`：25 项文本字节差异，包含 20 份 init rc 的旧 HIDL interface 行处理、一项指纹 VINTF 版本声明及四项行尾规范化。注释 interface 声明不等于 Android 16 不支持全部 HIDL，也不能替代对服务的验证。
- `apply_tinyxml2_vendor_fixups.py`：12 项现有厂商二进制改用原厂 `libtinyxml2_1.so`，避免加载不兼容新版 ABI。
- `fix_egl_mapper_getstub.py`：已知 ARM/ARM64 EGL 与 ARM64 Vulkan 的 mapper 调用使用 getStub；校验完整原始摘要和指令上下文，拒绝未知版本。
- `configure_adreno_symlinks.py`、版本化 makefile：Adreno 驱动保留 egl/ 中的规范副本，通过相对符号链接共享，避免重复加载单例状态。
- vendor 打包表采用实际 WSL 选择，排除与构建生成的 build.prop、NOTICE、目录链接冲突的条目；原始私有文件仍保留在本地清单中。

## 设备树中的实现

源码震动 HAL 与幅度映射、源码 Wi-Fi 服务及 RRO、蓝牙服务接入、厂商相机接入与辅助镜头策略、颜色模式 RRO、圆角/挖孔/状态栏覆盖均在 `device/meizu/m2381`。没有保留旧 M2468 指纹机器码修补入口。

此前强制 `debug.hwui.renderer=skiavk`、`debug.renderengine.backend=skiavkthreaded`、`service.sf.prime_shader_cache=false` 三项已删除；正常 OpenGL 路径的修复仍保留。

## 环境与诊断改动

历史 WSL 树把部分源码 HAL 移出扫描范围。该做法（构建前把目录改名到 `out/m2381-disabled-sources`）已废弃并移除工具：目录改名后项目仍在 manifest 中，打包阶段 `repo manifest -r` 必然失败，且每次 `repo sync` 都会还原。现统一用 `local_manifests` 的 `remove-project`。历史 zip/unzip 包装、代理设置及删除 `.repo` 后的占位 manifest 不是正常构建依赖。占位 makefile 仅存放在 `diagnostics/source-snapshots` 说明历史状态，不自动应用。无法仅凭失去 Git 元数据的旧树证明所有源码差异都已枚举。

旧树还保留重建的 `bionic/libc/kernel/uapi/misc/adsp_sleepmon.h`，已归档到 `diagnostics/source-snapshots`。它来自早期尝试编译源码音频栈的阶段；当前使用原厂音频 blobs、排除对应源码，不自动安装这个未经驱动 ABI 验证的头。

当前诊断启动参考另见 `diagnostics/README.md`；它不与平台补丁一起自动安装。
