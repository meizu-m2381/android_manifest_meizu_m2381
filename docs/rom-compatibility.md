# LineageOS 系 ROM 复用

主体是 M2381 硬件适配，可复用到提供匹配接口的 LineageOS 衍生 ROM。
当前受测基线为 PixelOS 17 / Android 17；独立 LineageOS 及其他衍生 ROM
尚未完整编译和启动，不能直接标为支持。

| 内容 | 入口 | 迁移要点 |
| --- | --- | --- |
| 共用硬件配置 | `m2381-common.mk`、`m2381-identity.mk`、`device.mk`、`BoardConfig.mk` | 共用分区/驱动/服务，身份在 ROM common 后设置 |
| PixelOS 产品 | `custom_m2381.mk` | 继承 `vendor/custom/config/common_full_phone.mk` |
| LineageOS 产品 | `lineage_m2381.mk` | 继承 `vendor/lineage/config/common_full_phone.mk`，已注册 |
| 旧厂商 ABI | 官方 shim、linker fragment、固定摘要的 ELF 副本 | 目标树需提供匹配模块，不修改冻结 VNDK |
| 资源覆盖 | Settings、SystemUI、Aperture RRO | 核对目标包名、资源名、overlayable 和实际效果 |

使用目标 ROM 的 release 和构建目标，例如：

```bash
source build/envsetup.sh
lunch lineage_m2381-RELEASE-userdebug
TARGET_PREBUILT_KERNEL_HEADERS="$(get_build_var TARGET_PREBUILT_KERNEL_HEADERS)" m bacon
```

`RELEASE` 须替换为目标树值，`m bacon` 也不能套用于所有衍生 ROM。
其他产品前缀可新增小的 ROM 产品入口，复用共用硬件配置，避免复制整套设备树。

需审阅 Qualcomm CAF common、SM8550 sepolicy、所选 HAL、VINTF/FCM、旧 vendor
API33、两种架构运行库和预编译头接口。产品级源码排除保留上游项目，其他设备
可继续使用；这不能代替其他设备自身的构建验证。
未知输入不能关闭摘要检查后强行修补。诊断启动与硬件验收限制见 [功能状态](status.md)。
