# 自动亮度适配

## 原因与配置

设置中开启自动亮度后，屏幕仍按手动亮度运行。真机日志显示光线传感器
有读数，但 DisplayDeviceConfig 的背光/nit 数组为空，自动亮度输出背光数组
也为空，BrightnessMappingStrategy 无法创建映射，最终
`mUseSoftwareAutoBrightnessConfig=false`、`mBrightnessReason=manual`。

设备树新增 `configs/display/display_id_4630946981250209410.xml`，
安装到 product 的 `etc/displayconfig/`。使用本机实际物理显示 ID，
通过标准 DisplayDeviceConfig 提供屏幕背光到 nit 的映射；
FrameworkOverlayM2381 提供环境 lux 到 nit 的目标曲线。
不改公共 framework 或传感器 HAL。

原始数据来自魅族 20 官方 Flyme 12.6.0.0A 的 `framework-res.apk`：

- 官方固件页面：<https://foru.flyme.cn/firmwarelist-195.html>
- APK SHA-256：`b166f5f675075467a5f1aeeff4d4b4c7c0b5a9d1fd8f008dfd2c4c897db915de`
- `config_screenBrightnessBacklight` / `config_screenBrightnessNits`：
  28 个校准点，背光 17–4095，亮度 1.974–780 nit。
- DisplayDeviceConfig 使用 0–1 浮点背光，将原始值除以 4095；
  另加 (0, 0) 关屏端点覆盖 framework 的最小背光 0。
- `config_autoBrightnessLevels` / `config_autoBrightnessDisplayValuesNits`：
  隐含 0 lux 加 18 个环境光阈值，对应 19 个亮度值，范围 7.3–780 nit。

这同时替换旧设备树最高 1650 nit 的曲线，避免超出本机校准范围。
没有根据宣传峰值亮度添加 HBM、HDR 映射或杜撰面板校准数据。
原厂 APK、资源导出和校准核对结果只保存在本地，不随源码分发。

实现方式参考 LineageOS 官方已合入提交
[502620：r8s 使用 DisplayConfig 配置亮度映射](https://review.lineageos.org/c/LineageOS/android_device_samsung_r8s/+/502620)。
仅参考接入方式，未复制三星面板的数值。
AOSP 的 `DisplayDeviceConfig.loadBrightnessMap` 与
`BrightnessMappingStrategy.create` 是本次定位和验收依据。

## 验证

已核对官方 APK 摘要、28 个校准点、19 个自动亮度目标值，以及数组长度、
单调性和归一化端点。XML 通过语法检查。

完整包 `PixelOS_m2381-17.0-20261120-0117.zip` 编译通过，
SHA-256 为 `d35c55ec498174c959bceb9c7d16f64739cd6b517bbbdb52aede60d912f735df`。
整包/payload 签名、CRC、13 分区解包摘要及 AVB 链检查通过；
Android OTA B→A 创建真实 userspace snapshots，重启后合并清理完成，
A 自动 successful，13 分区回读摘要匹配，userdata UUID 和应用列表保留。

真机已从新 XML 加载 29 个映射点，`mUseSoftwareAutoBrightnessConfig=true`、
`mBrightnessReason=automatic`，AutomaticBrightnessController 已订阅光线传感器。
外部手电照明测试中，环境光约 103→4275 lux，背光 504→3206/4095；
移除照明后回到约 100 lux、523/4095。没有注入模拟传感器数据或重置学习模型。

用户仍反馈响应慢、分段变暗，以及遮挡后亮度条停在五十多。
完全覆盖正面后传感器仍报告约 132 lux，暗环境最低亮度与屏下光线补偿
尚未验收，不能将“开始自动变化”当作完整修复。
驱动 `actual_brightness` 恒为 0，以上背光值取自 `brightness` 和 framework，
不是亮度计测量。
本地日志位于工作区外层 `.local-flash/auto-brightness-20261120/`。
