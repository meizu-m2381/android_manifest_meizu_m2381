# 抬起亮屏适配

魅族 20 原厂 SSC 提供私有 `raise_wakeup`：类型 65539、字符串
`com.meizu.sensor.raise`、唤醒型 on-change。此前虽然设备打开了框架的抬起
能力配置，SystemUI 查找的标准 `TYPE_PICK_UP_GESTURE`（25）并不存在。

## 原厂事件的含义

真机拿放记录出现了 1、2、6、7 等值，不能把它们视为拿起角度或完成百分比。
同机官方 Flyme 12.6 SystemUI 的 `RaiseFlipperController$6.onSensorChanged()`
确认：6 触发唤醒；2 在前序状态不是 6 或 7 时触发唤醒；7 则参与放下后的状态
处理。本实现只沿用抬起判定，不复制原厂自动熄屏策略。

## 设备实现

设备仓库 `sensors.m2381.so` 包装原厂 Multi-HAL 2.1 子库 `sensors.ssc.so`，
保留所有原始传感器和私有事件，增加一个标准抬起手势别名。新增传感器具有
wake-up／one-shot 标志、`minDelay=-1` 和零 FIFO；事件值转换为标准标量 1。
标准接口触发后撤销自己的监听，有私有订阅者时保持底层传感器启用。

工作线程串行处理一次性解除监听；回调不在原厂线程内调用原厂启停接口。
事件附带监听代次及原始时间戳，避免取消或重新监听后的旧事件重放。转发前
保留原始 ScopedWakelock，直到新批次接管；没有新增长期唤醒锁或加速度轮询。

SystemUI 原有的开关与锁屏唤醒继续负责用户行为：

- `doze_pulse_on_pick_up` 控制抬起手势。
- `doze_pick_up_gesture_ambient=0` 表示唤醒锁屏，而非仅显示环境时钟。

持续遮挡实测发现，距离传感器已报告近距离时仍出现 LIFT 唤醒。本版以及
LineageOS 23.2 的 `DozeSensors.TriggerSensor` 构造路径默认将标准抬起接口标记
为 `performsProxCheck=true`，因此不能依赖 SystemUI 再做一次距离拦截。

设备适配层已补充原厂唤醒型距离传感器的共享订阅：当前启用周期内有效的远距离
读数才允许抬起触发，近距离、未知、无效和乱序旧读数均不允许唤醒。被遮挡的
动作不会消耗一次性订阅，解除遮挡后下一次正常抬起仍可触发。距离传感器与其他
客户端共用时，保持各自订阅归属，并在内部订阅结束后恢复外部批处理参数。
外部客户端在内部监听期间加入时，也会收到当前距离值，避免破坏 on-change
首次上报语义。没有修改公共 SystemUI，也没有屏蔽原厂距离接口。

全部变更位于设备仓库，公共 framework 与原厂二进制保持不变。双击亮屏不属于
本次修改范围。

## 验证状态

- 使用生产源文件的独立回归二进制已在真机通过：元数据、动作过滤、一次性
  触发／重新监听／取消、旧事件拒绝、私有订阅共存、无效 flush／注入／直接
  报告，以及唤醒锁传递检查。
- 实际动态加载原厂 SSC 的探针确认原有子库 43 个传感器全部保留，增加一个
  标准手势后为 44 个；另一个 dynamic 子库不受影响。
- 完整 OTA 已完成 B→A 安装、userspace 快照合并清理、自动成功槽位及 13 分区
  SHA-256 回读；userdata 与用户应用保留。包 SHA-256 为
  `844c3a2ed4cf12c710957663d1d081ed31553dab1fa39fdc2dfd1d95300890a0`。
- 安装后原有 52 条传感器枚举记录全部保留，新增 1 条标准手势；实际加载库摘要
  和配置匹配。SystemUI 已监听标准手势，传感器相关 AVC 为 0。
- 开关以关闭／开启／关闭／开启顺序检查：关闭时标准监听消失，开启时恢复，
  全程保持 Dozing，没有注册即误唤醒。ADB unroot 后 HAL、SystemUI 和显示服务
  PID 均保持不变，唤醒锁为空闲状态。
- 普通重启后开关保留为 1、标准传感器与 SystemUI 监听恢复，AOD／自动亮度服务
  正常自启。人工拿起已由用户确认自动进入明亮锁屏，系统日志连续记录三次
  `WAKE_REASON_LIFT`，来源为 `com.android.systemui:NODOZE pickup`。临时关闭
  开关后，用户重复拿起未亮锁屏，系统保持 Dozing；随后已恢复开启。
- 后续用户明确确认持续遮挡仍亮屏，现场日志也记录近距离与 LIFT 唤醒，旧版
  防误触验证失败。修正代码已增加模拟 HAL 边界回归，正式安装后的人工复测
  和长期误触率验证尚未完成，不能将旧版正常抬起结果当作修正版验收。

原始日志、临时探针和原厂 APK 位于工作区外层 `.local-flash/pickup-20261120/`，
不提交到 GitHub。独立行为测试不能代替整机误触率或长期功耗验收。

参考官方实现：

- [LineageOS Xiaomi 的私有 pickup 转标准手势](https://github.com/LineageOS/android_hardware_xiaomi/blob/lineage-23.2/hidl/sensors/1.0/Sensors.cpp)：仅参考接入方式，动作码使用本机原厂判定。
- [LineageOS 使用真实抬起传感器的提交](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm6250-common/+/364222)。
- [LineageOS SystemUI 抬起手势与距离检查参数](https://github.com/LineageOS/android_frameworks_base/blob/lineage-23.2/packages/SystemUI/src/com/android/systemui/doze/DozeSensors.java)。
