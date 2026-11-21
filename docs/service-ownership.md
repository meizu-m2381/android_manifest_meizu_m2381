# 硬件服务归属与运行修复

2026-11-21 对实际安装的 init、VINTF、进程、Binder、设备 fd 和日志做了交叉检查。
温控两套 HAL 确认同时运行；其余重复项应区分重复声明、闲置主栈和实际硬件争用。
本轮修复均留在设备配置及 vendor 独立兼容副本，公共 AOSP 源码保持不变。

| 功能 | 选择与原因 |
| --- | --- |
| Power | 保留源码 QTI AIDL，去掉原厂同名 init 与旧服务安装项；原厂旧进程原本没有运行 |
| Thermal | 保留原厂 HIDL 和 thermal-engine，停选源码 AIDL；composer、perf、limits、QVR 仍依赖旧接口，避免两套 HAL 初始化相同硬件阈值 |
| NFC | 保留实际持有 nq-nci 的原厂 NXP HIDL 及 eSE 扩展，停选第二套完整源码 AIDL 控制器栈 |
| BootControl | 保留源码 QTI AIDL（含 recovery），裁剪旧 HIDL 服务、rc、manifest；旧接口和实现库保留给其他消费者 |
| 定位/时间/中断 | loc_launcher、time_daemon、msm_irqbalance 各保留独立 rc 的唯一定义；原触发条件与 SYS_TIME 权限保留 |

安装项裁剪可用 `tools/configure_service_ownership.py /path/to/android` 重现，
工具保持原始提取文件不变。USB/USB Gadget、Health/原厂充电管理、sensor_aux/传感器
Multi-HAL、软硬件 codec 的职责各不相同，没有按名称相近批量移除。

## SLIM

本机 izat 配置启用了 SLIM。原厂 slim_daemon 缺少 `__emutls_get_address`
的动态依赖，开机多次链接失败。给独立兼容副本补上实际 LLVM
`libemutls_get_address.so` 的 DT_NEEDED，继续使用真实 TLS 实现。

查阅了官方 [472164](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/472164)
和 [425419](https://review.lineageos.org/c/LineageOS/android_device_motorola_sm8550-common/+/425419)：
其他设备移除 SLIM 的前提是定位配置未使用它，不能直接套到本机。

## 重复 VSYNC

原厂只有一个 composer。内核 uprobe 抓到同一 DRM fd、事件上下文、序号和时间戳
重复回调；不是两个 SurfaceFlinger，也不是日志级别问题。一次原厂取样 460 个回调
只有 246 个唯一事件。公开的 QCOM `HWEventsDRM::HandleVSync/SetEventState` 与
固定版本二进制反汇编相符：关闭监听时忘记仍在内核队列中的请求，且在读取事件前
重新登记、读取多个事件后又登记，会形成重复的待返回请求。

兼容副本 `libsdmdal.so` 只改四条指令：保留待返回标记至读完事件、读完后统一登记
一次、停用传播时保留队列状态。既不吞掉真实的新 VSYNC，也不关闭日志。
`configs/compat/libbase-fixups.json` 固定完整输入/输出 SHA-256、偏移及原字节；
工具检查范围、等长、重叠和原字节，未知库拒绝处理。原始 proprietary 文件保留。

对照 [LineageOS QCOM 显示源码](https://github.com/LineageOS/android_hardware_qcom_display/blob/lineage-23.2-caf-sm8550/sdm/libs/dal/hw_events_drm.cpp)。
没有找到可直接应用到本机原厂库的官方单独修复；上述四指令调整为本机适配。
候选库临时绑定测试五轮亮屏/AOD，重复警告为 0，另一次追踪 218 个回调全部唯一；
测试后已恢复安装库。整包安装后的结论另行记录，不能用候选测试替代。

## 双击震动

Android 17 在缩放解析之后才为不支持的 DOUBLE_CLICK 插入默认幅度波形，
真机复现向 HAL 传入非法 -1.0。HAL 继续拒绝非法幅度；设备通过已实现的
Tiktap 组合后端执行两次 CLICK，三档相对强度 0.5/0.75/1.0，只在后端可用时声明支持。
直接 Binder/芯片检查为 0 失败，包含有限完成与取消后第二脉冲不能重启。
framework 缓存支持列表，临时替换 HAL 无法刷新它，必须新启动后验收系统调用路径。

## 验证边界

真实 ARM ELF 与安装归属的主机回归 9 项通过，无跳过。
NFC 开关/进程正常不能代替读卡、HCE 和 eSE；温度列表正常不能替代持续负载热保护；
SLIM 启动不能替代室外 GNSS。RCS 注册、AOD 环境光亮暗档、SELinux enforcing
和长时功耗仍分别追踪，见 [功能状态](status.md)。
