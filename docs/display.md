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

设备专属 `m2381-aod` 在 init 的 late_start 阶段以 system UID 启动；仅当
内核报告 AOD=1 且档位仍为 2 时初始化暗档，不覆盖已有 0/1 档，也不写普通
背光。每秒检查一次，不持有唤醒锁，单调时钟等待不会唤醒已挂起的系统。
设备实现二进制两次熄屏循环均自动得到 AOD=1、档位=0。
目前提供固定暗档恢复，尚未实现原厂夜间时段与环境光自动切换亮暗档的策略。

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
