# M2381 振动修复（2026-11-19）

后续已从 Flyme 12.7 原厂备份确认标准场景映射，见
[Flyme 原厂振动调用链核对](flyme-haptics.md)。当前已安装第四轮系统档位兼容版，
用户主观触感验收尚未完成。下文先记本轮结果，再保留第一轮记录。

## 第四轮：保留原厂基准并恢复系统档位调节

- 第三轮将 LIGHT/MEDIUM/STRONG 全部设为 128，导致预设反馈忽略系统强度档位。
  该策略不适合直接用于当前 Android framework，现已修正。原厂波形及最高档
  128 基准保留，三档分别使用 64/96/128。相对比例参考官方 LineageOS Oplus
  输入 FF 通路的约 1/2、3/4、1，不能称作 Flyme 自身的三档 RAM 参数。
- 对照当前 VibrationScaler：系统 LOW/MEDIUM/HIGH 经 effect strength 传至
  HAL。普通触摸和物理交互分别读取 haptic_feedback_intensity 和
  hardware_haptic_feedback_intensity，不能只验证某个固定 gain 是否写入。
- WSL 编译 HAL 和诊断程序成功（4 分 4 秒，含构建规则生成）；95 项真机控制
  检查通过，四个预设的三档实际芯片增益均按 64/96/128 检查。
- 另实际修改上述两个系统设置键，等待 framework 确认 TOUCH/PHYSICAL_EMULATION
  生效，再通过不带强制标志的 feedback 0/25 触发长按与拖动。低/中/高六项均在
  原厂驱动记录中出现对应的 gain=64/96/128、waveform=3、loop=0 和实际 set_gain；
  关闭档两项没有启动原厂播放，共八项通过。不是仅向 HAL 直接传入三个枚举值。
- 检查结束完整恢复原值：haptic_feedback_enabled=1，两个 intensity 均为 3。
  未通过 GUI 拖动滑块，未据此声称所有应用的自定义时间波形均已回归。
- 当前 HAL SHA-256：
  `7418087c29b849c145a1a22b086c8e84b3bc114065726dd76b5dcfd4155cb919`。
  已在真机替换挂载源、重启 HAL 并核对摘要，服务 running，第三轮文件保留以便
  回退。不修改 AOSP、内核、固件和升压参数；既有重启/enforcing/全场景边界仍适用。

## 第三轮：恢复原厂基准力度

- 原厂普通预设只传 effect ID，不消费 Android effect strength。将四个预设统一
  恢复为驱动默认/停止入口的 0x80 基准，取消之前每效果 8/32/48/96 和轻中档
  40%/65% 的额外衰减。LIGHT/MEDIUM/STRONG 在此原厂兼容策略下使用相同增益，
  系统强度档位不会进一步减弱这些预设。时间波形仍支持显式幅度控制。
- on()、服务初始化和设备 init 增益也改为 128，setAmplitude 改为幅度乘 128
  后向零截断，合法正幅度最低保留 1；与原厂 MzVibrateThread 的比例核对。
- 原厂 on_off 确实可以继承增益：先设 32 再触发原厂三项，芯片 0x39 保持 32；
  先走原厂 enable 停止入口则三项均为 128，触发序列为 3/13/11。此项验证的是
  原厂驱动的继承和基准行为，不是已启动 Flyme 系统进行全场景测量。
- WSL 编译 HAL/诊断程序成功（4 分 5 秒，含构建规则生成），设备 rc 通过
  host_init_verifier。真机 95 项检查通过；增益检查已从读取缓存改为读取芯片
  0x39，另验证 0.1 幅度截断为 12。framework 拖动 25、长按 0、点击 1、预设 2
  分别选中 3/3/13/11，芯片增益均为 128、loop=0，并回到 GO/GLB_STATE=0。
- 当前真机 HAL SHA-256：
  `845ef3e27fedc63c54b940853081d8cfbc12a07408712e9bf957db0891a83a9c`。
  已替换既有 metadata 挂载源并重启 HAL，目标摘要一致、服务 running；保留第二轮
  二进制以便回退。Tremor 已打开供比较。未修改 AOSP、内核、固件、RTP 或升压设置。
  整机重启、enforcing、完整 CTS/VTS、全场景机械手感等价性尚未验证。

## 第二轮：采用 Flyme 标准效果的波形

- TICK/CLICK/HEAVY_CLICK 从 RAM 12/17/16 改为原厂效果 21000/31008/30900
  对应的 RAM 11/13/3；标准 DRAG_START 随 HEAVY_CLICK 使用 RAM 3。
  TEXTURE_TICK 继续使用 8。增益、强度比例、30 ms 完成预算和停止保护沿用第一轮，
  未改 AOSP、内核、固件或持续振动 on()。不是完整移植 Flyme 的 GPIO 触发通路。
- 固件摘要、校验和及新波形采样数量、完整尾部均通过校验。
- WSL 实际编译 HAL 和诊断程序成功（4 分 7 秒，含构建规则重新生成）。
  真机新程序 94 项 Binder/硬件控制检查通过；framework 反馈 25/0/1 和预设 2
  分别选中 3/3/13/11，loop=0，结束后 GO/GLB_STATE 均为 0。
- 首次额外 framework 检查因脚本把 `seq1 = 3[0x03]` 当作纯数字行而中断；
  修正诊断解析后单独复测 framework 四项通过，无需修改 HAL。
- 新二进制 SHA-256：
  `4f077ebd6ff1da45f37018b6b927236f446beca8926e40c245480ff434139e53`。
  已替换既有 metadata 挂载源并重启 HAL，真机挂载目标摘要一致，服务 running。
  原第一轮文件在 metadata 与本地诊断目录保留，既有启动挂载路径不变。
  未重启整机，未重测首轮已有的崩溃恢复，未做 enforcing、完整 CTS/VTS 或长时验收。
- Tremor 已打开供用户比较；主观是否改善不能由软件检查替代。

## 第一轮记录

## 问题和方案评估

用户反馈不同场景都是“嗡嗡嗡”。真机实际运行源码
`android.hardware.vibrator-service.meizu`，与 WSL 旧构建产物 SHA-256 一致：
`5c696bc85908eaf540dbf6c36ecb0c4369a67431f9fcb96c5d83e3d699da0055`。
底层为 I2C `3-005a` 的 Awinic AW8697 LRA；没有发现切成转子马达模式的证据。

旧方案的独立马达通路、幅度控制、停止计时器和退出保护有价值，适合早期功能
接通。但四类 UI 效果均使用 `waveform=1`，仅用 8/12/18/30 ms 和增益模拟，
会提前截断完整波形，不能作为完成触感适配的依据。framework 当前触摸强度为
HIGH，是手感的影响因素，但不是共用波形问题的修复。

## 官方依据

先检索 LineageOS GitHub/Gerrit，再对照本机接口和固件验证：

- [344562：AW8697 区分效果和超时处理](https://review.lineageos.org/c/LineageOS/android_hardware_oplus/+/344562)，已合入。
- [335282：避免前一个效果残留波形配置](https://review.lineageos.org/c/LineageOS/android_hardware_oplus/+/335282)，已合入。
- [496379：替换有嗡感的点击波形](https://review.lineageos.org/c/LineageOS/android_device_osom_ingot/+/496379)，已合入。
- [513314：不虚报完成回调能力](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_interfaces/+/513314)，已合入。

其他机型的波形编号、电压范围和固件不同，不能直接复制。Gerrit 中尚未合入的
`haptic_hv` RAM 长度/效果映射系列仅作为交叉参考，未修改或替换本机内核。

## 修改范围

只修改 `device/meizu/m2381/vibrator` 的服务、设备 init 权限和诊断测试，并更新
设备策略注释；本工具仓记录验证。不修改 AOSP 源码、原厂内核模块或固件。

TEXTURE_TICK/TICK/CLICK/HEAVY_CLICK 分别使用本机 RAM 8/12/17/16 号短脉冲，
完整自然播放约 5.8/9.6/9.7/9.7 ms。30 ms 是包含异步驱动启动的完成预算，
保持在驱动单次播放阈值 50 ms 以内，不能误用为长振动时长。

每次先取消上一次播放，再明确设置波形；`on()` 恢复基础波形，避免持续通知与
点击互相继承配置。保留独立停止计时器和异常退出保护。未新增组合原语、频率
控制或回调能力声明。

本机 `waveform` 解析十六进制、`enable` 解析十进制，已使用明确的 `0x` 编码。
固件校验和、编号、样本数和 ABI 详情位于设备仓 `vibrator/README.md`。

## 验证记录与边界

- 已校验原厂固件摘要、校验和、20 项波形表和所选短脉冲完整收尾。
- 已通过 root sysfs 原始接口分别播放四个选定波形，确认正确十进制编号、
  `loop=0`，不写停止命令也能回到 GO=0 / GLB_STATE=0。
- WSL 实际编译 `android.hardware.vibrator-service.meizu` 和
  `m2381-vibrator-check` 成功；含重新生成构建图约 9 分 28 秒。构建仍输出既有
  设备 makefile 覆盖安装规则等警告，不将它们计为无警告全量构建。
- 同一诊断程序在旧版出现 31 条不符合新映射预期的断言；修复版全部 94 项通过，
  覆盖四效果三强度、硬件编号和 loop、自动停止、幅度、抢占、旧计时器取消与
  非法输入。31 条断言不是 31 个相互独立的旧版缺陷。
- 通过 `cmd vibrator_manager feedback` 分别执行 constant 1/9/23/0，framework
  记录 CLICK/TEXTURE_TICK/TICK/HEAVY_CLICK 全部 finished，内核记录选到
  17/8/12/16 且 loop=0；另验证 100 ms 通知和 280 ms 渐变幅度波形均结束。
- 在 2000 ms 振动期间强制终止 HAL，100 ms 后 GO/GLB_STATE 均为 0，
  init 停止保护生效；服务自动重启，重启进程的二进制摘要仍为修复版本。
- 设备侧 `vibrator-meizu.rc` 已通过构建树的 `host_init_verifier` 语法检查；
  此项不等于整机重启验证。
- 修复二进制 SHA-256：
  `761b3d8d1e58118771d275128e75f3f4fe28d0f549329bf7b54242138c5a3a65`。
  已在当前真机加载，进程为 system 用户、`hal_vibrator_default` 域，
  waveform 节点为 system:system 0660，沿用 `vib_strength_sysfs` 标签。
- 当前只向开发手机交付独立 HAL 二进制并 bind mount，原只读 vendor 镜像保留。
  已在现有 metadata 诊断入口追加下次启动挂载与节点权限配置，未据此宣称全新
  镜像刷入或重启回归通过；正式构建从设备仓 init rc 安装相同权限。
- 本次真机 SELinux 为既有 permissive 状态。metadata 挂载交付出现
  init 到 HAL 域的 `nosuid_transition` AVC；HAL 的 KernelLogger 写
  `/dev/kmsg` 也有修复前已存在的 AVC。未扩大策略掩盖这些问题，未验证 enforcing
  模式。正式 vendor 镜像内安装不经过本次 metadata 交付路径，仍需独立验收。

原始日志、固件分析输出、旧二进制与运行时交付备份保存在本地诊断目录，
不提交真机日志和编译产物。初次原始接口探测暴露了十六进制解析差异；后续
使用 `0x` 的复测确认编号正确，不能将初次编号错误的探测当作通过证据。

以上电气/软件观测不能替代加速度仪测量和用户握持体验。完整 CTS/VTS、长时
稳定性、来电可感知度、正式 OTA 安装和全部第三方应用场景未由这些检查覆盖。
