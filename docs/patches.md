# 兼容修补与迁移

当前 Android 17 的兼容处理留在设备/vendor 配置和独立副本中，不包含平台源码补丁。
官方实现、原理和兼容边界见 [平台隔离](platform-isolation.md)。

## 当前构建使用的修补

| 内容 | 配置/工具 | 处理范围 |
| --- | --- | --- |
| 旧 libbase 与 32 位媒体 ABI | 设备 `configs/compat/`、`tools/configure_blob_compat.py`、`tools/prepare_media_helper.py` | 固定摘要，生成独立 vendor 兼容副本 |
| DPM 旧 HIDL ABI | 同一固定摘要修补清单，官方 `libhidlbase_shim` | 64 位 `vendor.libdpmframework.so` 兼容副本 |
| QCRIL 短信开机优化 | 固定摘要兼容工具与官方 419259/418511 | 两项 64 位库副本等长改名，原始输入与数据库不变 |
| 原厂 IMS/RCS 组件 | vendor 的 `ims-stack.mk`、`rcs-stack.mk` | 同机 APK/Java HAL 库及当前 platform 签名；RCS 仍有开通限制 |
| 默认选网与 NR 信号刻度 | 设备 vendor 属性与 CarrierConfig RRO | 双卡默认自动模式、国内运营商 NR 按各自原厂 LTE 或平台 LTE 回退刻度校准 |
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
