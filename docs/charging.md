# M2381 充电信息适配（Android 17）

## 源码归属

`device/meizu/m2381/health` 基于 QTI 的 AIDL Health 入口和 AOSP
`libhealth_aidl_impl`，保留关机充电入口及忽略 UCSI 伪电源的初始化。
产品选择 `android.hardware.health-service.m2381`，不再安装原厂 Health
可执行文件、init rc 或 VINTF fragment；原厂输入本身仍完整保留。
重新生成 vendor 安装规则后执行：

```bash
python3 tools/configure_health.py /path/to/android
```

服务仍使用 `vendor.health-default` / `vendor.charger` 的 init 名称，独立的
可执行文件路径由 `hal_health_default_exec` 标记。AIDL 声明对应 Android 17
的 V5；不能直接将本目录复制到缺少匹配 Health 接口的旧 Android 分支。

## 修正范围

- 原厂 fuel gauge 的 `charge_counter` 单位是 mAh，转换为接口要求的 µAh；
  单独查询和 HealthInfo 回调使用同一转换，缺失查询仍返回错误。
- 固件的 `65535 * 60` 秒是无效估时，映射为未知 `-1`，不显示 45 天。
- 原本报告 Charging，且 USB online=1、输入电流=0、输入限流=0、电池
  电流为负，同时没有无线或 dock 供电时，报告 Not charging，并清除估时。
  不因瞬时净放电、满电小电流或读取失败误判。
- SystemUI 两个快充分界资源统一为 20W，5V/3A 的最大能力按普通充电显示。
  界面仍按电源最大能力分类；这不等于瞬时输入功率或电池净功率。

本适配只读取电源节点，不写入限流、充电开关、温控或 PD 参数。
本节 Health 信息适配不清除固件 USB_ICL=0 投票；底层后续修正见下节，不能将信息修正解释为
已经消除了底层零限流故障。

## 验证

在已配置的 Android 17 构建 shell：

```bash
m android.hardware.health-service.m2381 SystemUIOverlayM2381 m2381_health_policy_test
out/host/linux-x86/nativetest64/m2381_health_policy_test/m2381_health_policy_test
```

测试包含实际故障输入、正常恢复、满电/负载、缺失节点、估时哨兵、
电量计单位与溢出。真机还须核验 `dumpsys battery` 和
`dumpsys android.hardware.health.IHealth/default`，以及独立 charge counter /
status 查询、重启后的资源阈值和实际输入电流。主机测试不能代替这些检查。

### 本次真机结果（2026-11-15）

ARM64 服务编译成功，主机 6/6 用例通过。匹配 Android 17 的
host_init_verifier 已通过服务 rc 与临时挂载片段校验。
对整份设备 file_contexts 的策略检查受现有未定义的
`vendor_jiiov_fp_device` 条目阻断；这不是本次新增条目，不能据此声称
整份设备策略已通过验证。本次新增 Health 标签另单独核验。

在保持电脑连接的真实重启复现中，USB 在线、电流/限流均 0、电池负电流。
替换服务后 HealthInfo、独立 status 查询和 BatteryService 均为 Not charging，
估时 -1；独立 charge counter 查询与 HealthInfo 均为 4272000µAh。
重启后两项快充阈值均为 20000000，SystemUI 对 15W 报 normal（1），
原先为 fast（2）。

用户同口拔插后，输入限流恢复 3A，输入约 1.619A，电池净充入约
1.560A；HealthInfo 与独立查询均恢复 Charging，估时 480 秒，仍显示
普通充电。运行文件的 SHA-256 与本次编译产物相同。
真实大功率充电头的快充显示尚未验证；无效估时哨兵通过回归测试验证。

当前真机使用已保留原始内容备份的 metadata 早期 bind mount 装载
Health 可执行文件和静态 RRO，以避免重刷整包。未更改启动/AVB 分区，
没有擦除用户数据。普通后续构建使用源码模块及 RRO，不依赖这两个临时
挂载；刷入包含修复的完整镜像前应移除对应挂载。原第 47 组材料未改动。
临时采样服务已从启动入口移除，没有启用 charger_ulog。

在 Health 显示修复阶段，底层零限流仍可在重启后复现，同口拔插可恢复；后续驱动兼容修正见下节。双 USB 栈和旧诊断的
Gadget 开关不一致是另外发现的问题；仅停旧服务时 ADB/ICL 正常，
未取得足够证据将它们认定为零限流根因，本提交不修改该栈。

## 重启后电脑零输入：PD 与 USB 枚举限流兼容

2026-11-15 已在当前 M2381 / Android 17 / 原厂 5.15 模块组合中复现并修正：
一直连电脑重启时，USB 已在线并协商 PD 5V/3A，但输入/限流均为 0、
电池持续放电，固件生效项为 `iusb0_tot: USB_ICL: 0`。物理同口拔插可恢复。

跟踪确认，USB Gadget 枚举的 2mA/500mA 请求经 `usb_psy_set_icl` 发送给
原厂固件。原厂驱动接受 SDP、CDP 和 PD 三类 USB 枚举限流；本组合在 PD
连接启动时发生冲突。直接写限流、控制器软复位和 UCSI 重新绑定均未恢复；
单独改变 PD Gadget 描述符也不能防止从正常取电状态重启后复发。

兼容副本仅把 `usb_psy_set_icl` 的类型掩码 `0x4a` 改为 `0x0a`，
保留 SDP/CDP 的枚举限流，PD 由固件协商与既有温控投票管理。
没有设置固定电流，没有修改 PD 合约、温控、充电终止或看门狗。
不要把这项改动解释为通用固件修复，或直接套用到其他机型/驱动。

这是**原厂模块的二进制兼容修正**，不是自编译内核驱动。
原始 `modules_prebuilt` 与 `proprietary` 输入均保持不变；单独副本位于
`vendor/meizu/m2381/compat/vendor_dlkm/lib/modules/qti_battery_charger.ko`，
安装名称仍为 `qti_battery_charger.ko`，Android.mk 明确选择该副本。

```bash
# 默认只核验；缺少副本、未知输入、输出被改动时均失败。
python3 tools/configure_pd_icl.py
# 向已同步的 Android 工作区复现（保留原输入）：
python3 tools/configure_pd_icl.py --root /path/to/android --apply
```

工具核对 ELF 架构、节位置、原指令、整文件前后 SHA-256，拒绝未知输入
和冲突输出；重复应用不改写文件。输入/输出与方法见
`provenance/charging-pd-icl.json`。更换原厂版本时必须重新分析，不能跳过摘要校验。
将来有匹配源码时应在源码中实现类型检查，并重新验证 SDP/CDP/PD 与热管理。

### 真机回归与交付边界

同台电脑、原数据线全程连接，前三次正常重启后输入分别约
1.553A、1.366A、0.934A，电池净充入约 1.420A、1.323A、0.943A；
限流均保持协商所得 3A，USB_ICL=0 不再出现。电量 97%→99%，
接近满电时电流自然下降。Android 完成启动、ADB 在线，文件传输摘要一致。
移除临时跟踪后的第四次重启输入约 1.294A、电池净充入约 1.104A，电量充至 100%。撤回的 USB HAL 描述符试验未进入最终补丁；运行的是原 USB HAL。

真机通过 metadata 早期 bind mount 交付兼容模块，保留原始入口与自动回退，
没有刷写启动/AVB/逻辑分区或清除数据。该挂载必须在模块加载前完成，
系统运行后覆盖磁盘文件不能替换已加载模块。完整新系统镜像安装后应移除
该临时挂载，避免覆盖后续版本。原厂内核本来允许未签名模块；本次没有
关闭签名验证。不能将此作为启用严格模块签名设备的通用修改方式。

用户随后完成快充头连接约 20 秒再接回同台电脑。返回后 USB 在线，
输入约 0.862A、ICL 3A、ADB 正常，启动 ID 未变化。内核原有日志记录了
本轮多次插拔及在线期间 ICL 3A，没有复现此前零限流。定时离线采样
已在实际操作前结束，因此本轮切换证据来自内核日志与返回后的快照，
不能称定时采样完整覆盖了切换。

测试时已满电，充电头在线阶段日志仍为 PD 5V/3A；本轮验证了电源切换
兼容性，没有验证大功率快充或更高电压合约。普通 SDP/CDP 端口、低电量
大功率快充和长期满充/温控回归仍需分别验证。满电降流不视为零限流复发。

Android 17 实际模块安装目标构建成功，安装文件摘要与真机副本一致。兼容工具的幂等执行、未知输入拒绝、冲突输出保护和临时文件清理均已验证；5418 项固定输入完整校验零错误。
