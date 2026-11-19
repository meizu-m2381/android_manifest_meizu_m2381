# M2381 振动修复（2026-11-19）

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
