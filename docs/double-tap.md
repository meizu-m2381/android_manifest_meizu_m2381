# 双击亮屏适配

魅族20原厂触摸屏已能在熄屏时识别双击，但此前系统不处理其私有键码。
实际内核日志记录 `get DOUBLE-TAP gesture` 与
`mz_gesture_report: gesture 0x270, mask 8300011f, pos 5`；同机原厂
`goodix_ts.ko` 确认固件双击码0xcc映射624，单击625，指纹按压626。
原键表仅将143映射为WAKE，因此单纯设置SystemUI双击开关不会建立驱动事件通路。

## 设备实现

设备传感器子库新增 `com.meizu.sensor.double_tap`，唤醒型一次性接口，handle
`0x00f00002`，类型65541。framework设备overlay的
`config_dozeDoubleTapSensorType` 指向此类型字符串；SystemUI使用已有的
`doze_pulse_on_double_tap` 设置与双击唤醒流程。

保留 `doze_double_tap_proximity_check=true`，由SystemUI读取距离状态并拦截遮挡
事件。原始624不映射成WAKE，避免绕开系统开关和距离判断。原有抬起亮屏、指纹、
AOD与全部原厂传感器保留，未修改公共framework源码或内核二进制。

输入按 `main_touch` 名称与624键能力查找，不假定event编号。监听期间以BOOTTIME
读取evdev，只接受新624按下和完整SYN_REPORT帧。单击、指纹、释放、重复按键、
旧输入及丢帧不生成手势。关闭监听或一次性触发后关闭输入fd，工作线程通过
eventfd阻塞等待；不独占触摸屏、不注入按键、不合成触摸坐标、不持有常驻唤醒锁。

传感器服务补充 `input` 组；设备策略补充查询输入设备与设置fd时间基准的ioctl。
原厂手势mask初始化保持现有配置，开关控制的是SystemUI与HAL监听；关闭功能
不代表触控固件停止所有手势识别，因为同一驱动还服务指纹。

## 当前验证

- 正式Soong模块和回归二进制编译通过；回归在真机运行通过，覆盖真实
  input_event格式、单击/指纹/释放/重复过滤、一次性/重订/取消、旧输入与
  SYN_DROPPED、设备缺失和唤醒锁归属。抬起与距离共享的既有回归仍通过。
- 完整Android OTA已完成B→A安装、真实userspace快照合并清理、自动成功槽位与
  13个分区SHA-256回读，userdata与用户应用保留。包SHA-256：
  `abc96672f54932c3381be162edd80f6ceea29f4ccff328730d55ab3340e996cb`。
- 原有52条传感器记录全部保留，新增抬起与双击两个手势；实际加载库摘要、
  overlay和服务补充组匹配。关闭／开启四次检查与监听状态一致；ADB unroot后
  HAL、SystemUI与显示服务PID保持不变，没有传感器相关新增AVC。
- 普通重启后两个手势监听与显示服务自动恢复，开关保留开启；关闭AOD后，双击
  与抬起仍保持监听，已恢复原AOD设置。实际HAL以system身份、input补充组打开
  main_touch，传感器唤醒锁空闲时未持有。
- 实体屏幕双击、关闭开关后的实体双击、遮挡及关闭AOD后的实体双击仍等待人工
  操作；当前尚未记录到新包的实体双击事件。解析测试与监听检查不能代替行为验收。

参考：

- [LineageOS SystemUI 双击传感器注册与开关](https://github.com/LineageOS/android_frameworks_base/blob/lineage-23.2/packages/SystemUI/src/com/android/systemui/doze/DozeSensors.java)。
- [LineageOS 唤醒与距离检查流程](https://github.com/LineageOS/android_frameworks_base/blob/lineage-23.2/packages/SystemUI/src/com/android/systemui/doze/DozeTriggers.java)。

原厂模块、反汇编、事件和安装日志保留于工作区外层 `.local-flash/doubletap-20261120/`，
不提交到GitHub。
