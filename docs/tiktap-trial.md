# M2381 标准组合原语试用记录（2026-11-19）

当前版本已于 2026-11-20 随完整系统安装到 B 槽，已提交并推送。
HAL 摘要仍为 `f9699b469fd995073aeabddcad5c14d15f49682a2752c6a7e8558e95162288f8`，
重启不再恢复旧 HAL。镜像交付、策略修复与重启后的验证见
[完整安装记录](full-system-install.md)；下文保留此前临时试用过程。

在 [原厂组合研究](tiktap-composition.md) 之后，用户授权替换体验。仅修改设备仓，
复用原厂算法、参数和波形，不修改 AOSP、内核模块或固件。本次为临时 HAL 试用，
不是正式 OTA、全量 CTS/VTS 或长期稳定性验收。
用户反馈滑条呈连续嗡振，并要求先不提交。本轮设备与记录提交已撤回，改动保留
为未提交状态；触感尚待用户确认，不以控制检查通过代替主观验收。

## 实现

- 标准原语：NOOP、CLICK、THUD、SPIN、QUICK_RISE、SLOW_RISE、QUICK_FALL、
  LIGHT_TICK、LOW_TICK。THUD/SPIN 在末节补齐；具体曲线见设备仓 `vibrator/README.md`。
- 普通 RAM 预设继续使用 Flyme 8/11/13/3 映射、64/96/128 三档；DRAG_START
  在当前 framework 中仍为 HEAVY_CLICK。组合能力会用于 SystemUI 滑条等调用。
- 原厂算法的 detached 工作线程隔离到每次请求的独立工作域子进程。取消先终止并回收
  旧生产进程，再发 RTP STOP，避免旧线程往新请求的共享区写入。
- 每项输入验证原语、scale、delay 和长度，最多 16 项、每项 delay 最大 1000 ms。
  amplitude 固定 128，framework scale 转为曲线强度；scale=0 使用最小输出，
  不传入原厂 amplitude=0 的默认峰值分支。NOOP 只等待，不启动算法。
- 完成以首次消费后的完整时间线加余量为依据，子进程 off 后退出，父进程确认
  退出并再次 STOP 才回调；保留 generation 取消与看门狗。不会以“最后块已消费”
  作为完成。on/perform 回调能力仍未声明。
- 设备 init 覆盖并禁用原厂 Tiktap HIDL，确保共享区只有一个所有者。追加源策略
  和实际使用的 API 33 CIL 权限；HAL 异常退出的 init 规则增加 RTP STOP。

## 已执行验证

1. WSL 编译服务和设备检查程序成功，包含构建图生成约 9 分 29 秒。
   既有设备 makefile 覆盖安装规则等警告仍存在，不视为无警告全量构建。
2. 新 init rc 经 host_init_verifier 通过；追加 CIL 复用现有分区策略，通过
   compile_split_policy.py / secilc。该工具沿用既有 `-N`，不等于 neverallow
   或 enforcing 验收。
3. 真机 Binder / 驱动检查 **184 项 PASS、0 failures**。包含原有 RAM 映射、三档
   gain、时间波形和停止检查，以及七原语回调、五段 LOW_TICK、非法参数、取消
   等待中的请求、RAM/RTP 双向抢占、连续 20 次请求替换。
4. 重启 zygote 刷新 framework 能力缓存，dumpsys 确认 COMPOSE_EFFECTS，七项原语、
   时长、size=16、delay=1000 均被系统识别。安装脚本最初将重启期间 pidof 返回
   非零误当错误，已修正等待处理；随后手动补验缓存和恢复触觉开关，没有重刷系统。
5. 通过 framework TOUCH 请求两个 scale=0.3 的 LOW_TICK（中间 delay=400 ms），
   系统低/中/高档分别缩放为约 0.21/0.30/0.41。实测子进程收到的曲线峰值参数
   分别为 29/37/46；关闭档没有创建生产进程，framework 记录 ignored_for_settings。
   这是实际请求参数与路由验证，不是加速度或人体感知强度测量。
6. 五个 LOW_TICK、scale=0.3、delay=0 的滑条模式通过 framework 正常结束，
   played 保留五项原语，没有回退为普通时间波形；日志总时长约 116 ms。
7. 在五段 SLOW_RISE 播放期间 SIGKILL HAL：生产子进程随之退出，约 100 ms 后
   开始的寄存器检查确认 GO/GLB_STATE=0；HAL 自动重启，后续 LOW_TICK 请求
   finished。运行镜像中的旧 init 保护已通过这次检查，新 rc 的额外 STOP 规则
   仅做语法检查，尚未通过整机重启验证。

原语回调实测比“delay + 查询时长”保守约 27–59 ms；其中包含进程加载、驱动
启动、主动停止与回调开销，不等于波形本身被拉长。该版本优先用于验证触感和
路由，进程启动开销、快速拖动时感知延迟、长序列/高负载欠载、功耗、音量/亮度
实际拖动的主观手感仍需继续验证，不作为最终低延迟调校结果。

## 用户试听后的第二版调整

首版 LIGHT_TICK/LOW_TICK 使用 6/12 ms 连续包络，五段没有间隔时容易连成
连续振动。用户反馈滑条“嗡嗡嗡”，因此首版主观验收不通过，已先回退旧 HAL。
第二版将两项都改为原厂带制动瞬态：LIGHT_TICK frequency=100，取模型波 15
的 272 样本，约 11.33 ms，报告 12 ms；LOW_TICK frequency=20，取模型波 3
的 564 样本，23.5 ms，报告 24 ms。两者点强度基准分别为 25/35，继续应用
framework scale。原厂制动尾部完整保留，不通过截断持续振动模拟点击。
该映射依据模型波表及原厂索引算法，不宣称触感已经通过用户验收。
第二版已重新编译并临时安装，184 项控制检查再次通过；framework 识别
LIGHT_TICK=12 ms、LOW_TICK=24 ms，系统三档和关闭再次通过请求参数检查。
安装脚本等待条件改为具体能力及非空效果表，避免读取系统初始化期间的空信息。
第二版 SHA-256：
`41eca9881d586d12f178573f171cdf994c4359c081821039a4583d3ac04297df`。
重启恢复旧 HAL 的方式不变，已重新打开 Tremor。代码和记录保持未提交。

## 临时试用阶段的交付与恢复（已由镜像安装取代）

- 手机序列号 `381QYFCN223WJ`，实际马达 AW8697。
- 首版试用 HAL SHA-256（已撤回，当前版本见末节）：
  `be69fc8dd79170aa1195f4cf5461d6fc5baa95b5d01fdc56198d0d7f3e29667d`。
- 旧 HAL SHA-256：
  `7418087c29b849c145a1a22b086c8e84b3bc114065726dd76b5dcfd4155cb919`。
- 当前临时 bind 源：`/metadata/bootdiag/vibrator-composition-20261119/service.all-primitives`。
  在既有 HAL bind 上叠加，未覆盖原启动源文件，也未改写启动入口。
  共享挂载传播会使旧源路径当前也显示新版本；用非递归父目录 bind 观察底层
  文件，已确认原文件仍为旧哈希，检查用挂载已清理。
- **整机重启后恢复旧 HAL 与原厂 HIDL 服务**。无需重启的恢复脚本保存在
  本地 `.local-flash/haptics-20261119/install_composition_trial.py --rollback`，
  它移除试用层、恢复两项服务并刷新 framework 缓存。
- 当前 `vendor.meizu.vibrator=running`、原厂 Tiktap HIDL 为 stopped。
  恢复本轮开始时用户触觉开关=1、触摸/硬件反馈强度=3/3；已打开 Tremor 供用户比较。
- 设备仍为既有 permissive，未热加载本次 SELinux 策略；不能将编译通过作为
  enforcing 或正式镜像验收。原始日志、旧版本、构建产物和恢复工具均在
  `.local-flash/haptics-20261119/`，不提交进源码仓。

## 补齐 THUD / SPIN 的试用版

用户反馈 LOW_TICK 高频反馈分不开后，上一轮已将其时间槽调为 36 ms：
保留原厂 23.5 ms 完整瞬态，尾部约 12.5 ms 静默；五段仍为五段，不合并
framework 的标准请求。该版哈希为
`9a708b08642f29012c3c960f0943c7f00e15d7ce9cf3d6a4ca5a2eee1f168164`。

本轮仅在设备 HAL 中补齐 Android 的两个可选原语，保留 CLICK=20 ms、
LIGHT_TICK=12 ms、LOW_TICK=36 ms 及既有 RAM 预设/档位：

- THUD=60 ms：0/6/18/60 ms，强度 0/100/35/0，frequency=20。
  用低频撞击后的衰减包络表达下坠撞击。
- SPIN=100 ms：0/25/70/100 ms，强度 0/70/100/0，frequency=10/30/80/100。
  用渐增能量和频率表达旋转动量，尾部归零。

frequency 是原厂抽象控制参数，不是 Hz。这两条是按 Android AIDL 定义
适配的设备曲线，未找到对应 Flyme 标准原语参数，不能宣称完全复刻原厂手感。
每个原语仍只有一个四点事件，最大时长仍为 100 ms，因此未扩大原有 worker
输入长度、事件数、时间线或幅度范围；不涉及 AOSP、驱动、固件或校准改动。

WSL 增量编译 HAL 和诊断程序成功；既有 TARGET_SCREEN_WIDTH 警告仍存在。
真机检查 **203 PASS、0 failures**，覆盖九项原语的时长/回调/硬件待机、
THUD+SPIN 带间隔组合、16 项 SPIN 播放中取消、未知原语拒绝，以及旧 RAM、
五段滑条、跨模式替换和快速取消回归。新原语查询时长加 15 ms delay 后，
THUD/SPIN 回调分别约 131/180 ms，仍有原有进程/停止开销，不能当作低延迟验收。

重启 zygote 后 framework 识别全部九项（含 NOOP），THUD=60 ms、SPIN=100 ms。
通过 framework TOUCH、scale=0.3 请求两项，过滤确切四点时间线以避免误抓用户
滑条进程，低/中/高档两项峰值均为 29/37/46；关闭档无对应生产进程，并记录
ignored_for_settings。测试后设置恢复为 1/3/3。
重新打开 Tremor，原语区 SPIN/THUD 均可用；framework 记录其应用请求分别以
Primitive=SPIN/THUD 完成。主观触感仍由用户比较，不以路由或控制检查替代。

当前 HAL SHA-256：
`f9699b469fd995073aeabddcad5c14d15f49682a2752c6a7e8558e95162288f8`。
安装采用新文件 `service.all-primitives` 替换临时挂载，未覆盖开机基线；
整机重启仍恢复旧 HAL。`composition-trial.json` 已更新，原恢复脚本可继续使用。
本轮代码与记录继续保持未提交。新增检查记录为 `device-check-all-primitives.txt`、
`all-primitives-system-levels.json` 和 `tremor-all-primitives.png`。
