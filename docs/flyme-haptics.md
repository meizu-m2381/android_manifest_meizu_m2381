# Flyme 原厂振动调用链核对（2026-11-19）

## 来源与结论

从本机原始分区备份
`C:/Users/zhaiy/Documents/Project/meizu20/backup/partitions/super.img` 的 `system_a`
只读提取 Flyme 12.7.0.0A 的 `framework.jar`、`services.jar`，分析 DEX，
并对照现有原厂 `haptic_hv.ko` 的 ARM64 反汇编。未运行 Flyme 整机抓取，
以下是静态确认的标准 API 通路，不代表所有 Flyme 桌面私有交互。

原厂 fingerprint：

```text
meizu/meizu_20_CN/meizu20:16/BQ2A.251016.001-BP2A.250605.031.A3/1764128685:user/release-keys
```

| 文件 | SHA-256 |
| --- | --- |
| framework.jar | 81dd4e81561c973e6bb5f726b077a9a20a98f619d0c33266776835c35638f648 |
| services.jar | 666473bf5c1ff4980b90edba66a5657c6fab8370fa7761e75d6ce0b211b391e0 |
| haptic_hv.ko | bbb1806a45cdfb44a45d2763e19f912c80e8e5d03a9dc007dd5476a0e2dce23f |

## 标准场景和原厂波形

`android.os.FlymeVibratorHelper` 有两张不同的映射表，不能把 Android 场景 ID、
Android 预设效果 ID、Flyme 效果 ID、RAM 波形编号混为一谈。

| 调用场景 | Flyme 效果 ID | 驱动 RAM 波形 |
| --- | --- | --- |
| LONG_PRESS(0)、CONFIRM(16) | 30900 | 3 |
| VIRTUAL_KEY(1)、KEYBOARD_PRESS(3) | 31008 | 13 |
| CLOCK_TICK(4)、CONTEXT_CLICK(6)、KEYBOARD_RELEASE(7)、VIRTUAL_KEY_RELEASE(8)、TEXT_HANDLE_MOVE(9) | 21000 | 11 |
| REJECT(17) | 31003 | 进入驱动效果表查找，本次未继续解析 |
| 标准 DRAG_START(25) | 先取 HEAVY_CLICK(5)，再转 30900 | 3 |

预设效果表 `sFlymeVibrationEffectId`：CLICK(0) → 31008，DOUBLE_CLICK(1) →
31003，TICK(2) → 21000，HEAVY_CLICK(5) → 30900。场景表
`sFlymeViewEffectId` 没有直接登记 DRAG_START(25)。

### DRAG_START 的完整标准调用链

1. `services.jar` 的 `HapticFeedbackVibrationProvider.getVibrationForHapticFeedback`
   对 25 进入默认分支，调用 `VibrationEffect.get(5)`。
2. `framework.jar` 的 `VibrationEffect.get` 创建 `PrebakedSegment`；该类的构造函数
   调用 `checkNeedUseFlymePrebackedEffectId`，在普通非 CTS 模式将 5 转为 30900。
3. `VibratorManagerService.startVibrationOnThreadLockedFlyme` 对普通应用的
   Mono/Stereo 效果进入 `mzVibrateThreadRunning`。当前包中的
   `useFlymeNotRichtapVibrator()` 返回 `!isCtsRunning()`；shell 调用另有分支，
   因此不能用 shell 在原厂系统的行为直接代替普通应用。
4. 非通知的普通预设效果交给 `FlymeVibratorHelper.performEffect(30900)`，
   写入 `/sys/class/meizu/motor/on_off`。
5. 原厂模块 `aw8697_on_off_store` 将 30900 对应到 RAM 3，设置触发正向序列
   寄存器 0x15，随后通过 GPIO 触发。它与当前 HAL 的 `waveform/enable` 路径
   不完全相同，不能仅比较波形编号就宣称输出强度、制动和全部手感一致。

复核锚点：services classes3.dex 的方法 code_item 为 0x27cb10，指令起点
0x27cb20；0x2c 的 packed-switch 使用 0x8c 的 payload，firstKey=11、size=17，
key=25 的目标是 0x73，返回效果 5。PrebakedSegment 构造方法 code_item
0x2e7594；模块函数 0x7198，30900 分支在 0x7330–0x7340。

## 对当前修复的影响

第一轮修复使用 TEXTURE_TICK/TICK/CLICK/HEAVY_CLICK → RAM 8/12/17/16，
是根据固件短脉冲和驱动播放行为选出的映射，**不是已还原的 Flyme 原厂映射**。
原厂 HEAVY_CLICK 实际使用 RAM 3，而不是 16。按既有固件解析，RAM 3 为
374 个采样（24 kHz，约 15.58 ms），RAM 16 为 232 个采样（约 9.67 ms）；
这些采样时长不等于用户感受到的机械振动持续时间。

此前 94 项控制检查证明第一轮实现符合其设定的映射、停止与抢占行为，
不证明其触感等同原厂。用户仍反馈硬点击感，因此主观触感验收尚未完成。

系统还包含 RichTap、RealityTap 适配类和 `.he` 文件路径，但类存在不代表
M2381 标准反馈实际经过这些路径；不能据此直接套用其他机型的 `.he` 配置。
通知和来电还有独立 RTP 选择，本表不覆盖其全部策略。

## 力度通路的进一步核对

- 普通预设在 `mzVibrateThreadRunning` 中读取 PrebakedSegment 的 effect ID，
  交给 `performEffect(id)`；此分支不读取 effect strength。此前 HAL 的
  每效果 8/32/48/96、LIGHT/MEDIUM 40%/65% 衰减不是此 Flyme 通路的参数。
- `aw8697_enable_store` 在 0x77b8–0x77dc 将默认增益设为 0x80，再解析可选参数；
  停止入口 0x7964 也向 set_gain 传 0x80。`aw869x_set_gain` 把参数低 8 位
  写入芯片 0x39。基准为 128，不是硬件最大可编码的 255。
- `aw8697_on_off_store` 并非每次无条件设置 128：0x7274 的字段条件成立时才重设，
  其他情况下继承既有寄存器。真机先写增益 0x20，再分别触发原厂效果
  30900/31008/21000，0x39 仍为 0x20；先走原厂 enable 停止入口后再触发这三项，
  0x39 均为 0x80、0x15 分别为 3/13/11，并自然待机。因此不能把继承值误读为
  每个场景自己的固定力度，也不能宣称本次抓到了 Flyme 开机后的全部动态状态。
- 原厂初始化 `aw869x_misc_para_init` 在 0xf454 起读取硬件 0x39 并缓存到 gain，
  不在该处另写某个场景增益。已从同一 super 只读核对 vendor/system/system_ext/
  product 的 init rc，涉及马达的脚本主要配置节点权限，没有发现对这条 Awinic
  通路写入此前 0x30 或分效果力度的规则。
- Flyme 的时间/幅度波形在 `MzVibrateThread.run` 0x70–0x77 将浮点幅度乘 128
  后转整数，再传给 `FlymeVibratorHelper.vibratorOn`，最终作为 enable 的第二参数。
  HAL 保留其比例和向零截断；合法正幅度最低保留 1，满足正幅度接口边界。
- `FlymeVibrationSettings` 中还有触觉默认 213、其他默认 255 的用户设置，
  它们不能直接作为本机 RAM 增益：普通预设分支只传 effect ID，且驱动对持续
  播放大于 128 的数值另有折算。不能把设置值 213 不加分析地写入增益寄存器。

本次复原的是已确认的 **128 基准和普通预设无额外档位衰减**，以及显式时间波形
幅度的 128 比例，不是移植原厂整套应用/RTP/全局状态机。与波形复原一样，
实际机械手感及全场景等价性仍需独立验证。

用户随后要求安装比较，第二轮已将 HAL 的 HEAVY_CLICK/CLICK/TICK 改为原厂
3/13/11 波形，当时保留此前增益；第三轮按上述依据恢复原厂基准力度。
两轮均保留 waveform/enable 触发通路，未改 AOSP；构建与真机检查
见 [振动修复记录](haptics.md)。此前试听的 RAM 19、约 50 ms 平滑振动方案
没有设为系统默认。触发参数及 Flyme 桌面私有场景仍需单独核对，主观触感待用户验证。

原始提取文件和定向 DEX dump 保存在 WSL `/home/zhaiy/m2381-haptics-work`，
不将原厂 JAR、分区镜像或临时反汇编产物提交到源码仓。
