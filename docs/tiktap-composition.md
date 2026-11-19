# M2381 Tiktap 与 Android 组合原语接入研究

本文保留接入前的研究结论；后续经用户授权安装的临时版本与验收结果见
[组合原语试用记录](tiktap-trial.md)。

## 范围与结论边界

研究对象为备份 super 中的 Flyme 12.7.0.0A Android 16 原厂实现，以及当前
M2381 真机的 AW8697 / haptic_hv 驱动。Android 源码仅作只读接口核对，
独立诊断模块不加入 PRODUCT_PACKAGES，不替换系统 Vibrator HAL。

原厂具有私有动态波形组合能力；这不等于原厂已经在实际 AW8697 通路中实现
Android 的 CompositePrimitive。接入标准组合原语还需要设备 HAL 的波形映射、
尺度转换、播放调度、抢占及完成通知。

## 原厂通路证据

从同一份 super 只读重新提取下列文件，与 vendor 仓对应文件逐字节相同：

| 文件 | SHA-256 |
| --- | --- |
| lib64/vendor.qti.hardware.vibrator.impl.so | 35401f194f7ee95745bfe7f4ee1fdb2894c8369891bbfb88a9734df4f416d9b0 |
| lib64/hw/tiktap_algo.default.so | 10d0933df9540f48f2136737b2fea3b9a96ffce0dd7446530fe2d51a0f394684 |
| lib64/hw/vendor.meizu.hardware.tiktap_hidl@1.0-impl.so | 6143920bf26c93424b45aa39a92f641a4327c169d5d2294eb4ea173d68451561 |
| firmware/tiktap_config.txt | 69397a2e10b514fe0f7b1e14718f19d7d95dc70897cf73a5661f3652a61479bb |
| firmware/tiktap_params.bin | 5bb0b13e945e85e58dc7ea728d5fe630b9854c127b4e100952f6223c12c6c279 |
| firmware/tiktap_wave.bin | c46738aae57077b95f4326329a65acdfa6730752e892c0d6ad72c5101cc5507b |

- 原厂高通 AIDL 库有 compose / getSupportedPrimitives，列表为 0–8，但其
  InputFFDevice 构造方法仅接受 qcom-hv-haptics / qti-haptics 输入设备。
  不能用这份通用库的符号或返回列表证明本机 AW8697 已实现标准原语。
- 原厂 services.jar 的 startVibrationOnThreadLockedFlyme 将普通 Mono / Stereo
  请求转入 mzVibrateThreadRunning；该循环只分支处理 PrebakedSegment 和
  StepSegment，没有 PrimitiveSegment 分支。shell / CTS 有特殊路径，因此
  shell 的结果也不能直接代表普通应用的 Flyme 路径。
- 私有 Tiktap HIDL 提供 dynamicEffectOn_hidl、dynamicEffectOff_hidl、
  dynamicEffectUpdate_vib_info_hidl，通过共享内存向算法库传数据。
- tiktap_config.txt 指定 /proc/tiktap_buf。当前真机的这个节点存在；
  /proc/kallsyms 中 tiktap_init、tiktap_proc_ops、tiktap_work_routine、
  tiktap_unlocked_ioctl 都属于 haptic_hv，与 AW8697 驱动同模块。
- 算法库包含瞬态、四点连续曲线、波形重采样、模型波形及制动处理。
  普通 on 路径和 ringtone_vib_with_f0_cali 是不同入口；研究不调用后者，
  也不读取会触发硬件校准的 sysfs f0 节点。

## 上游参考

先核对 LineageOS 官方 Gerrit，再设计本机方案：

- [459856，已合入](https://review.lineageos.org/c/LineageOS/android_hardware_samsung/+/459856)，
  b7341a295cded396704d82fc66441d1a889710ef：原语应对应独立波形、时长和尺度，
  组合交给设备后端执行。其 Cirrus/Samsung 波形索引不适用于 AW8697。
- [436411，已合入](https://review.lineageos.org/c/LineageOS/android_vendor_qcom_opensource_vibrator/+/436411)，
  6ae8473f274d27c11291fc27f25908e54fdf6a6b：实际缺少 primitive_duration
  后端时不应声明 CAP_COMPOSE_EFFECTS。接口存在不代表后端功能完整。
- [482407，已合入](https://review.lineageos.org/c/LineageOS/android_hardware_sony/+/482407)，
  66547d8d7d81941b402ac425a3612f7882fa327d：组合不能只计算时长而漏掉实际
  原语队列写入；验收必须观察硬件播放。
- [513872，待审核](https://review.lineageos.org/c/LineageOS/android_kernel_ayn_cq8725s-modules/+/513872)，
  9e84739aad7eabb8b8d2c162aeede87f038d56ce：在另一款 haptic_hv 内增加
  FF 原语和时长节点。仅用于交叉核对 ABI，不作为本机可直接套用的成熟实现。
  M2381 当前使用原厂预编译模块，也不能把这份内核补丁当作已有能力。

当前 AIDL VTS 在 CAP_COMPOSE_EFFECTS 开启时要求 CLICK、LIGHT_TICK、
QUICK_RISE、SLOW_RISE、QUICK_FALL；NOOP 是 AIDL 定义要求。
LOW_TICK 是当前 SystemUI 滑条连续反馈使用的原语。因此仅实现 LOW_TICK
或把所有 ID 都映射成同一个 CLICK，不足以完成接入。

## 私有协议静态还原

原厂库导出的入口：

- tiktap_open(const hw_module_t*, const char*, hw_device_t**)：加载配置、参数、
  模型波形，映射驱动共享区。
- on(tiktap*, void*, int)：解析并启动内部线程，返回不表示机械播放完成。
- off(tiktap*)：请求停止并发出 ioctl 0xff0b。

在本机 64 位库中，on 的 payload 按 int64_t 解析，开头依次为：

| 字段 | 静态观察 |
| --- | --- |
| loop | -1 或非负值；诊断仅使用 1 次 |
| interval | 循环间隔，0–1000 ms |
| amplitude | 全局幅度，0–255；0 有特殊含义，见下文 |
| frequency | 全局频率参数，不应直接当作 Hz |
| eventCount | 事件数量 |
| 每事件的 pointCount | 只接受 1 或 4 |
| 每点 | 时间、强度、频率三个 int64_t；强度和频率为 0–100 |

一个点对应瞬态；四个点描述连续曲线。原始反汇编和诊断日志保留在工作区
外部研究目录，不向源码仓提交原厂二进制或完整反汇编。

tiktap_params.bin 的十个字节为 AA 18 A0 B4 7F 13 0A 00 00 03。
按原厂加载和日志分支解释：f0_pre=170、play_freq=24 kHz、连续频率范围
160–180 Hz、短振峰值 127、连续峰值 19，另有低频及制动配置。
这些是 Tiktap 的样本生成参数，不能直接替代 RAM gain 或 Android 用户档位。

## 接入必须处理的问题

1. 幅度 0 不能直接作为静音传入：原厂线程仅对全局幅度 1–255 应用比例；
   0 会采用配置中的默认峰值。Android 用户关闭必须在启动前拦截，正幅度
   量化也不能意外落到这个默认分支。原语 scale=0 的接口含义为最低可感幅度，
   同样不能不加转换地写成原厂默认峰值。
2. on 的第三个长度参数没有在已检查的解析分支中形成输入边界保护。
   包装层必须验证事件数量、点数、实际字节数、时间顺序和总时长，不能把
   未验证的应用数据交给原厂库。
3. 算法使用全局状态、全局共享缓冲区、互斥锁和 detached 工作线程。
   新 HAL 与原厂 Tiktap 服务不能各自同时拥有同一播放设备；需要明确唯一
   播放所有者，并处理 RAM 与 RTP 两种模式之间的停止和恢复。
4. 私有接口没有 Android IVibratorCallback 完成语义；不能在 on 返回时
   回调完成。需要以实际数据消费及硬件状态确认完成，取消时淘汰旧回调。
5. 需要分别设计 CLICK / LIGHT_TICK / LOW_TICK 和上升、下降包络，保持
   原语之间的差异。已有 Flyme 预设效果映射不等于这些标准原语的原厂映射。
6. 用户强度通过 framework 的原语 scale 进入组合，必须保留低/中/高差异；
   不能因复用原厂峰值而重现此前三个强度全部 128 的问题。

## 真机隔离验证：2026-11-19

独立 arm64 C 诊断程序通过 dlopen 调用上述原厂库。运行前停止当前设备 HAL
与原厂 Tiktap HIDL 服务，暂时关闭系统触觉，避免多个客户端竞争。程序只在
进程内打开算法调试日志，不修改原厂配置、校准或固件。每个模式均有外部超时，
结束后停止马达，恢复服务和原先的触觉开关。

所有事件使用全局 amplitude=128、frequency=50，事件峰值 intensity=40；
这是用于验证协议的固定测试条件，不是拟定的 Android 原语力度标定。

| 模式 | 输入 | 生成结果与驱动观察 |
| --- | --- | --- |
| init | 打开算法与 mmap | 返回 0，复测约 0.18–0.24 ms |
| transient | 0 ms 处单个瞬态 | 467 个样本，约 19.46 ms；ready → consumed |
| continuous | 0/5/30/35 ms，强度 0/40/40/0 | 840 个样本，35 ms；ready → consumed |
| sequence | 0/25/50/75/100 ms 的五个瞬态 | 三个块共 2867 样本，约 119.46 ms；三块均被消费 |
| cancel | 0/5/175/180 ms 的连续曲线 | 4320 个样本；约 35.1 ms 调用 off，3.60 ms 返回，约 39.2 ms 共享区清空 |

上述五个模式退出码均为 0。生成长度依据完整 ready 块及原厂算法日志核对；
不能使用仍为 invalid 状态、正在填充的块计算波形长度或峰值。
非初始化模式的 on 调用约 1.03–1.23 ms 返回，首块约 4–6 ms ready。
这些只是该次带调试日志的运行记录，不代表最坏延迟、机械起振时间或性能保证。

内核日志确认进入 `aw869x_play_mode: enter rtp mode` 和 GO=1。
取消模式中，STOP ioctl 的内核时间戳为 11099.979494，GO=0 为
11099.979654，工作线程退出为 11099.981041。最终每个模式在统一清理后读取
GO=0、GLB_STATE=0，未出现卡住持续播放。未使用加速度计测量机械停止时刻。

共享区为 16 个 1024 字节槽，status 位于偏移 0、长度位于 2、样本数据位于
21，每槽最多 1000 个样本；0xff/0x55/0xaa 对应 invalid/ready/consumed。
**consumed 只说明驱动已取走数据，不说明芯片 FIFO 已播完或马达已经停止。**
例如五段序列最后一个块约 61.9 ms 被取走，但数据自身长约 119.46 ms；
不能在最后一个 consumed 时发送 Android 完成回调。

首轮探测曾在播放中读取 sysfs `reg`。该节点整块读取需要约 110–120 ms，
并持有驱动锁，明显干扰时序。因此首轮的取消结果和延迟数据作废，复测改为
播放时仅观察 mmap 共享区，结束清理后才读寄存器。即使是只读观测，也不能
直接把整块寄存器轮询放进未来的低延迟播放调度器。

恢复后，当前 HAL 的 95 项设备控制回归全部通过、0 failures；两项服务均为
running，触觉开关恢复。设备 HAL SHA-256 前后一致：
`7418087c29b849c145a1a22b086c8e84b3bc114065726dd76b5dcfd4155cb919`。
这项回归验证已有波形映射、档位增益、停止及替换控制；不代表完整 CTS/VTS、
机械触感或新组合原语验收。没有修改 AOSP 源码、替换当前 HAL 或开启组合能力。

当前原厂 Tiktap HIDL 服务还存在 vendor_file 标签/域转换及 proc 访问的
SELinux denial，日志显示 permissive=1。研究程序能在当前环境运行，不证明
适用于 enforcing 的产品环境；正式接入必须在设备策略中处理权限和服务域。

## 接入判断与建议

结论是**原厂 Tiktap 可作为本机标准组合原语的候选 RTP 后端，基础生成、
驱动消费和主动停止已经真机证实；完整标准 HAL 接入尚未完成**。

优先在设备自有 Vibrator HAL 内做有边界的 Tiktap 包装，保留当前 RAM 预设和
普通 on/off 路径。组合需由唯一播放所有者一次提交完整时间线，不能由应用侧
循环调用现有 CLICK 代替。先解决与原厂 HIDL 的所有权，再处理跨模式抢占。

按 Android 语义分别标定瞬态、轻 tick、低频 tick、快速/缓慢上升及快速下降
包络，完成 scale 映射、时长查询、延迟/大小限制和输入校验。不能宣称这套
新映射就是 Flyme 的标准原语参数，原厂私有组合能力没有提供这样的证据。
当前 SystemUI 连续滑条请求五个 scale=0.3、delay=0 的 LOW_TICK，正适合用
完整序列验证；它必须在各次反馈和用户强度档位之间保持预期差异。

完成通知需要独立解决 FIFO 排空与机械播放的时序，不能照搬算法线程结束、
on 返回或共享块 consumed。还需覆盖连续拖动时的新请求替换、off 和回调竞争、
算法异常/进程退出后的硬件停止、系统低/中/高/关闭、enforcing、重启及完整
VTS。完成这些之前，维持当前不声明 CAP_COMPOSE_EFFECTS 的行为。

本轮诊断源、构建日志、JSON 结果及内核日志保留在工作区外层
`.local-flash/haptics-20261119/`；原始库、定向 DEX dump 和反汇编保存在
WSL `/home/zhaiy/m2381-haptics-work/`。临时诊断模块不作为 ROM 产品模块保留。
