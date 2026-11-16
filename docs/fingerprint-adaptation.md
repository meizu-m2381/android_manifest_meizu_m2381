# M2381 屏下指纹适配（2026-11-16）

## 故障与修正

指纹 HAL 正常注册并被设置识别，但录入圆环落在屏幕底部之外。
设备树 `configs/properties/vendor.prop` 使用了不适用于本机的中心
`(632,2460)`、尺寸 `208×208`；本机屏幕为 `1080×2400`，纵坐标已经越界。

以随仓保存的原厂 `proprietary/vendor/build.prop` 为依据，恢复：

```properties
vendor.meizu.fingerprint.in-display=true
vendor.meizu.fingerprint.x=540
vendor.meizu.fingerprint.y=1796
vendor.meizu.fingerprint.width=190
vendor.meizu.fingerprint.height=190
```

标准 AIDL `IFingerprint/default` 由 `qfp-daemon` 提供，传感器为高通
QFS4008 屏下超声波；`vendor.meizu.hardware.fido@2.0-service` 是独立扩展服务。
原设备树中“没有 UDFPS”和“fido 提供标准接口”的注释已纠正。
本轮只调整设备属性，不修改 AOSP、不新增 HAL shim，不套用 JIIOV/HBM 方案。

## 验证

- 修正前 AIDL 查询返回中心 `(632,2460)`、半径 `104`，截图显示圆环越界。
- 现有镜像通过诊断入口 `on init` 设置等价属性，保存原件并核验摘要，
  正常重启后 AIDL 返回中心 `(540,1796)`、半径 `95`。
- 用户确认图标位置正确、成功录入，锁屏后指纹解锁成功。
- 系统状态确认已录入 1 枚指纹，2 次成功认证，HAL deaths=0。
- 诊断入口通过 `host_init_verifier`；设备树已同步到 WSL。

当前真机仍依赖 metadata 诊断入口，正式镜像交付使用设备树的 vendor 属性。
本轮没有全量刷写 ROM。应用 BiometricPrompt、支付认证、熄屏长时间待机后解锁、
多枚指纹和模板重启持久性尚未完整验证。

原始截图、日志和诊断入口备份保留在私有 `.local-flash/`，不纳入公开仓库。
