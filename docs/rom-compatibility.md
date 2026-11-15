# LineageOS 系 ROM 的复用范围

本项目的主体是 M2381 硬件适配，包含设备树、RRO、原厂预编译输入和兼容修正，并非只能用于 PixelOS。但“基于 LineageOS”不保证分支间的构建接口和运行接口完全相同。

| 层次 | 当前放置位置 | 迁移时的处理 |
| --- | --- | --- |
| 设备公共定义 | `m2381-common.mk`、`m2381-identity.mk`、`device.mk`、`BoardConfig.mk` | 两个产品共用，分区、驱动、设备服务与标识不依赖 PixelOS 产品名；标识仍在 ROM common 之后应用 |
| PixelOS 产品 | `custom_m2381.mk` | 继承 `vendor/custom/config/common_full_phone.mk`，产品为 `custom_m2381` |
| LineageOS 产品 | `lineage_m2381.mk` | 继承 `vendor/lineage/config/common_full_phone.mk`，产品为 `lineage_m2381`；现已注册到 AndroidProducts |
| ROM 自身构建入口 | lunch release、构建目标、签名/更新配置 | 使用目标 ROM 的分支约定，不能把 `m pixelos` 用于所有 ROM |
| 平台源码兼容改动 | libbase、VNDK、头生成及可选 TurboAdapter 补丁 | 前五项源于硬件兼容需求，但补丁上下文属于已记录的源码基线；第六项仅涉及 PixelOS GMS 构建 |
| 资源覆盖及相机 | Settings、SystemUI、Aperture 的 RRO | 检查目标资源名、overlayable、包名和相机应用，不能只验证 XML 能解析 |

## 同基线迁移

优先选择 Android 16、LineageOS 23.2 对应分支。完成 [构建准备](build.md) 中的固定输入核验、设备目录同步和平台补丁审阅后，在目标 ROM 中使用：

```bash
source build/envsetup.sh
# RELEASE 使用该分支定义的 release token，不保证每个分支都为 bp4a。
lunch lineage_m2381-RELEASE-userdebug
m bacon
```

`m bacon` 是 LineageOS 的入口；衍生 ROM 使用其自己的目标。某些 ROM 将产品前缀改成 `crdroid_`、`aosp_` 等，应新增一个小的 ROM 产品文件，继承 `m2381-common.mk` 及该 ROM 的 common 配置，再注册到 AndroidProducts，不要复制一整套硬件配置。

LineageOS 产品入口已经完成基础解析检查；**尚未在独立的 LineageOS 源码树上编译和启动验证**。当前真机验证来自 PixelOS 16.2。Android 17、其他 Lineage 版本以及所有衍生 ROM 均不能因此直接标为支持。

## 需要审阅的接口

目标树需提供 Qualcomm CAF common 配置、SM8550 sepolicy、设备所选 HAL 源码和相应 Soong 配置。VINTF/FCM、旧 vendor API 33、32/64 位运行库、libbase 符号、驱动 mapper 调用、SystemUI/Settings 资源都要对齐。平台工具拒绝未知源码摘要时，应移植相关兼容修改，不能关闭校验后强套二进制指令补丁。

固定驱动文件解决了输入版本一致性；当前诊断启动链、permissive、未验证硬件和没有完整源码 revision lock 的限制仍存在。它们与选择 PixelOS 还是 LineageOS 是不同问题。
