# M2381 屏下指纹

本机屏幕为 1080×2400，使用原厂属性中的中心 `(540,1796)`、尺寸 `190×190`。
旧 donor 配置中心 `(632,2460)` 越过屏幕底部，导致录入圆环错位。
设备 `configs/properties/vendor.prop` 设置：

```properties
vendor.meizu.fingerprint.in-display=true
vendor.meizu.fingerprint.x=540
vendor.meizu.fingerprint.y=1796
vendor.meizu.fingerprint.width=190
vendor.meizu.fingerprint.height=190
```

标准 AIDL `IFingerprint/default` 由 `qfp-daemon` 提供，传感器为高通 QFS4008
屏下超声波；`vendor.meizu.hardware.fido@2.0-service` 是独立扩展服务。
不需要套用 JIIOV/HBM 方案。

已核对构建后的五项属性与 AIDL 返回的中心/半径一致，用户确认圆环位置、录入
和锁屏解锁正常。应用 BiometricPrompt、支付认证、长时间待机、多模板与重启
持久性尚未完整验收。旧诊断入口若设置同名属性，迁移时需核对是否覆盖正式配置。
