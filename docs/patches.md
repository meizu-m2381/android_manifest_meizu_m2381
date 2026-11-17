# 兼容修补与迁移

当前 Android 17 的兼容处理留在设备/vendor 配置和独立副本中，公共平台源码
无需六项历史补丁。官方实现、原理和旧工作区迁移步骤见 [平台隔离](platform-isolation.md)。

## 当前构建使用的修补

| 内容 | 配置/工具 | 处理范围 |
| --- | --- | --- |
| 旧 libbase 与 32 位媒体 ABI | 设备 `configs/compat/`、`tools/configure_blob_compat.py`、`tools/prepare_media_helper.py` | 固定摘要，生成独立 vendor 兼容副本 |
| PD 枚举限流兼容 | `tools/configure_pd_icl.py`、`provenance/charging-pd-icl.json` | 已知版本充电模块的独立副本 |
| tinyxml2 ABI | `tools/apply_tinyxml2_vendor_fixups.py`、`tools/verify_tinyxml2_vendor.py` | 已记录版本的 vendor 库 |
| Adreno mapper ABI | `tools/fix_egl_mapper_getstub.py` | 已记录版本的 EGL/Vulkan 库 |
| 原厂文本配置 | `patches/vendor-text-fixups.json` | 固定版本 init/VINTF 等差异与摘要 |

随附 vendor 仓已经包含兼容副本；一般构建只核验。需要从原始输入重新生成时：

```bash
python3 /path/to/android_manifest_meizu_m2381/tools/configure_pd_icl.py --root /path/to/android --apply
python3 /path/to/android/device/meizu/m2381/tools/configure_blob_compat.py --aosp /path/to/android --apply
```

更换未知版本驱动需重新移植和验证，不能跳过摘要检查或按旧偏移强套指令。
固定输入与原始副本见 [输入说明](local-inputs.md)，充电修补边界见 [充电适配](charging.md)。

## 保留的旧平台补丁

`patches/platform-17-series.json` 及其补丁保留给 `apply_platform_patches.py --restore`
识别并撤销旧 checkout 的修改，`--require-unpatched` 检查恢复结果。
恢复器先核验全部摘要，拒绝覆盖未知源码；Android 17 不允许重新 `--apply`。

Android 16 的 `platform-series.json` 仅保留旧基线和迁移依据，未按当前方案重验，
不属于当前受测构建流程。不要恢复旧的全局 HAL 排除、临时构建包装或占位头文件。
