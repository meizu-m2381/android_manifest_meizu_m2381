# 显示链路检查与设备适配

受测设备：魅族 20 / m2381，PixelOS 17 / Android 17，原厂 BOE 面板及显示 HAL。
本页记录 2026-11-20 的现场结果；独立测试与整包安装验收分开记录。

## AOD 进入后黑屏

用户反馈时钟先出现，随后实体面板变黑。系统处于 DOZE，SystemUI 截图中仍有
时钟、日期与通知，SurfaceFlinger 也报告 Doze。内核已执行 nor2aod，但
`/sys/kernel/display_drivers/aod_light_mode` 停留在未初始化值 2。

同机原厂 SystemUI 的 `DozeScreenBrightness.onScreenState()` 在进入 DOZE 后
延迟约 450 ms 调用 `updateDozeBrightness()`，单独向该节点写入 0 或 1。
内核模块反汇编确认这两个值分别发送原厂低亮度、高亮度 AOD 命令。
现场分别写入 1、0 后，用户确认时钟持续显示，暗档只是变暗，并未消失。

最初设备 `m2381-aod` 只将未初始化值 2 恢复为暗档。11月21日已补齐自动亮暗档：
现有设备系统服务在 AOD 中订阅普通非唤醒 ALS，按同机原厂 2/6 lux 回差选择
暗/亮档；vendor 服务作为唯一面板写入者应用该档位，并在本地 22:00–06:00
覆盖为暗档。亮屏后退订光感，新的 AOD 会话清理上一会话状态；无效数据或缺失
输入退回暗档。不修改正常背光，不新增唤醒锁、唤醒光感或唤醒定时器。
因此已挂起期间改变光线，需要等系统下一次已有唤醒才处理，不承诺即时更新。

阈值来自同机原厂 `SensorPolicy.updateAmbientLux()`：<=2 lux 暗、>=6 lux 亮，
中间保持；夜间时段来自 `AODStateController.checkNightMode()`。原厂 SystemUI
输入 SHA-256 为 `64fff7a78142cff0b8e8cd5aa138084605a54488ebbe045d76afc72700b3cde6`。
实现说明和边界测试在设备仓 `display-state/README.md`，没有复制原厂 Java 类。

光感补偿服务另外使用 PowerManager 的交互状态判断息屏；AOD 下 DPMS 仍可能
报告 On，不能据此继续采样。设备实现在 AOD 中两次均报告 interactive=false。

## 护眼、额外调暗与色彩矩阵

真机白屏对照中，未校正的局部截图在四种状态下始终返回 `ffffff`，而实际
显示矩阵分别为：

| 状态 | 矩阵对角线 RGB |
| --- | --- |
| 普通显示 | 1 / 1 / 1 |
| 护眼 2850 K | 1 / 0.749 / 0.509 |
| 额外调暗 50 | 0.522 / 0.522 / 0.522 |
| 护眼加额外调暗 | 0.522 / 0.391 / 0.266 |

因此截图像素不能直接代表经过全局变换后的面板 RGB。设备实现通过现有
`config_deviceSpecificSystemServices` 和 system_server classpath 扩展点加载
设备服务 `DisplayAuxService`，从 `DisplayTransformManager` 读取正在生效的
六级矩阵并按框架顺序组合，同时包含 SurfaceFlinger 的全局饱和度矩阵。
读取的是当前矩阵，包括框架动画过程中更新的值，不另行推算色温系数。
接口只允许 system UID 和 root 查询，不接受矩阵写入。

采样器对内存中最近一次 12×12 样本应用该矩阵，按当前线性／非线性模式处理
传递函数；普通 SDR 保留显示的 sRGB／Display P3 色域，不先裁剪为 sRGB。
色盲校正的独立 daltonizer 路径不在当前接口范围内，开启该路径时暂停补偿。
全部实现位于设备仓库，没有修改公共 framework 源码。

## HDR、安全窗口与受保护缓冲区

仅调用窗口的 HDR color mode 并未产生真实 HDR 图层，未计入 HDR 通过项。
随后使用本地测试程序的 10 位 EGL BT.2020 PQ 图层，SurfaceFlinger 的截图结果
确认为 HDR；PQ 1000 nit 白色在普通截图中已变成色调映射后的 `efefef`。
这些数值不能直接送入按普通面板 RGB 校准的补偿算法。设备实现检测到 HDR 时暂停
补偿，未宣称 HDR 下自动亮度补偿、峰值亮度或色准已经完成。

使用自建 EGL protected context／surface 验证，普通受保护缓冲区会在 GPU
截图中变成黑色，但 `capturedSecureLayers=false`。单独设置 protected Error
也没有让当前 Android 17 GPU 路径报错；FLAG_SECURE 和 protected 是两种状态。

当前框架的 DPU 预检会对受保护／禁止采集的安全图层返回 PERMISSION_DENIED；
显式 sRGB 的局部缩放请求在普通内容下返回 INVALID_OPERATION。设备实现利用这条
已在真机核实的预检区分二者，并在受保护内容期间暂停补偿；不采集受保护像素。
该行为依赖当前 SurfaceFlinger 实现，升级 Android 时必须重跑这些检查。

与生产采样器使用同一源文件的独立探针已验证：普通 SDR 白屏可采样；
HDR、受保护但未标记 secure 的缓冲区、protected+secure、安全窗口均被拒绝
作为补偿样本。测试没有使用用户的视频、账号或 DRM 内容。
这些结果不等同于商业 DRM 播放授权、Widevine 等级或 CTS/VTS 验收。

## 整包状态与边界

11月21日自动 AOD 包已完成 B→A OTA、真实 userspace snapshot 合并清理、自动
启动成功标记和 13 分区回读；userdata UUID 及原有应用保留。
包 SHA-256 为 `f2678ea1b7e96b07f109025bf3f6483fceecc45b25c48a1a15de98ba38cf1033`。
新控制器、native 服务和系统属性策略的实际包内内容核对通过，上一轮重复服务
整理和显示/震动修复仍保留。源码 neverallow、源码预编译策略和实际 API33 分离
策略编译通过；新增 AOD 相关 AVC 为 0，不代表全局 enforcing 完成。

正式包三轮亮屏退订/AOD重订通过，关闭 ADB root 后进程不变。用户再次确认实体
时钟遮光变暗、移开变亮；同步记录到 0.81 lux/面板暗档，随后 121.7 lux/面板亮档。
独立候选试跑还用仅影响测试进程的时区验证了夜间强制暗档，未修改手机时间/时区；
纯逻辑检查覆盖全天小时、22/6点边界、无效输入、回差与会话重置。
额外非root普通重启后控制器自启，非唤醒光感订阅、抬起/双击监听和 SLIM 均恢复。
本次 OTA 首次启动和额外重启的 crash buffer 均为空；上一包偶发音频初始化崩溃
尚未定位，不能因本次没有复现便标为修复。

以下是11月20日显示矩阵和光感补偿包的历史验收，不能扩大为11月21日全部重测。

完整 OTA 已执行 A→B 安装、真实 userspace 快照合并及清理，B 槽自动标记成功，
13 个分区回读 SHA-256 全部与包匹配，userdata 标识和用户应用保留。
包 SHA-256：`570b37cab2030743706e51847051ac3808c6043255d9e4cd5912222c6a167617`。

安装后，普通、护眼、额外调暗、组合四种状态的设备接口矩阵与 SurfaceFlinger
矩阵逐项对照，误差均小于 0.001（SurfaceFlinger 文本仅显示三位小数）。对应
白屏补偿 RGB 分别为 `ffffff`、`ffe0bd`、`bfbfbf`、`bfa88d`。
Display P3 EGL 图层也可正常采样，HDR／安全／受保护内容检查均再次通过。

在不透光织物覆盖正面的固定背光 523/4095 对照中，四种状态的黑白画面均为
0 lux；显式停用 DSP 补偿后白屏约 109.96 lux，重启正式服务后恢复 0 lux。
第一轮流式日志后段缺样，额外调暗、组合与补偿开关对照已用按进程日志补录，
没有把缺失样本当成 0。真实自动亮度下遮光背光降至 49/4095，理由为 automatic。
这些遮光结果不等同于全部环境下的照度线性或色准测量。

正式 AOD 服务两次熄屏均自动初始化暗档；关闭 ADB root 后两个设备进程 PID
保持不变，用户确认实体时钟持续显示。测试后已恢复原调试状态并清理临时 APK、
探针及手机上的 OTA 包。新增服务／节点相关 AVC 为 0。
系统全局 SELinux 仍为 permissive，不能据此声称 enforcing 或 CTS/VTS 已完成。
长时 AOD 功耗、烧屏位移、HDR 峰值亮度与全部色彩模式的仪器测量尚未完成。

现场证据位于工作区外层 `.local-flash/display-audit-20261120/`，不提交截图、
临时测试程序和原厂二进制。

参考过的官方实现与提交：

- [LineageOS DisplayTransformManager](https://github.com/LineageOS/android_frameworks_base/blob/lineage-24.0/services/core/java/com/android/server/display/color/DisplayTransformManager.java)
- [LineageOS SystemServer 的设备服务扩展点](https://github.com/LineageOS/android_frameworks_base/blob/lineage-24.0/services/java/com/android/server/SystemServer.java)
- [LineageOS 对 DOZE_SUSPEND 更新异常的处理](https://review.lineageos.org/c/LineageOS/android_device_lge_sm8150-common/+/383614)：故障表现不同，未照搬关闭低功耗状态。
- [LineageOS DisplayDeviceConfig 接入实例](https://review.lineageos.org/c/LineageOS/android_device_samsung_r8s/+/502620)：仅参考配置接入，亮度数值使用本机原厂数据。
