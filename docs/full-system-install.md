# 完整系统构建与安装（2026-11-20）

完整 `pixelos` 目标已在 WSL 编译成功并安装至开发手机 B 槽。七个逻辑分区
使用此次构建镜像，匹配 boot、init_boot 与 AVB；vendor_boot 继续保留已验证的
诊断 ramdisk、DT 和 bootconfig。未清除 userdata 或 metadata，未改 A 槽、
DTBO、modem。此结果不代表通用 recovery/OTA 或去除诊断依赖后的安装验收。

## 构建与版本

- 设备：`android_device_meizu_m2381`，`a2cc715`。
- 内核：`android_device_meizu_m2381-kernel`，`8c21aaf`。
- 厂商：`proprietary_vendor_meizu_m2381`，`e7f87b2`。
- 工具仓：构建时为 `e3d9bb7`，本记录另行提交。
- 配置：`custom_m2381-cp2a-userdebug`，完整目标 `pixelos`，退出码 0。
- 使用已有产物进行增量构建；Ninja 普通任务 24，highmem 池深度 1。
- 安装包：`PixelOS_m2381-17.0-20261119-0828.zip`，3,452,831,642 字节。
- 包 SHA-256：`37094056c26be82fbc16394836d2a52af8af0806fb94632208659137c0168f5c`，
  全包 ZIP CRC 检查通过。包内设备断言包含 m2381。

安装包已生成，但此次采用已验证的 fastbootd 分区安装路径；没有使用这个 ZIP
验证 OTA 升级。候选启动链保留诊断 vendor_boot，并重新生成匹配 AVB 元数据，
完整描述符和哈希树校验通过；使用测试密钥及原有开发验证配置。

## 构建中修正的设备问题

WSL 设备策略文件的 CRLF 导致 checkpolicy 报 `0xd`，按 Git 的 LF 内容规范化后
通过。没有修改 AOSP 源码或放宽检查。

原组合实现重执行同一 HAL 程序时使用 `execute_no_trans`，触发平台
`hal_neverallows.te`。对照官方 LineageOS 同条限制与 AOSP `domain_auto_trans`，
改为从 `hal_vibrator_default` 自动进入非 HAL 域 `vendor_tiktap_worker`。
只配置父子进程控制、原厂库读取、日志及 Tiktap 节点/两个 ioctl；波形、力度、
LOW_TICK 36 ms 和 SystemUI 五段请求不变。

源码预编译策略和 neverallow 检查通过，实际安装的原厂 API 33 分离策略合并
编译通过。后者仍使用既有 init 兼容路径；设备依旧 permissive，不能据此声称
完整 enforcing 或 CTS/VTS 验收通过。

## 镜像与刷写验证

已备份当时的九个相关分区、完整 super 及诊断 metadata 文件，并校验摘要。
刷写 odm、system、system_dlkm、system_ext、vendor、vendor_dlkm、product 后，
在诊断 recovery 中解析实际 super extent，对七个分区逐一回读 SHA-256，均与
候选镜像一致；启动分区回读也与候选一致。

完整解包并核对 35 项关键文件，覆盖震动 HAL/init/策略、IMS/CNE、QCRIL、
RIL 数据库、DPM 和官方 shim、充电模块、框架及运营商 RRO。框架 RRO 与受测版
功能资源一致；完整构建额外生成伪语言资源及 SDK/打包属性，不影响正常语言
配置。Carrier RRO 的编译资源及 manifest 与受测版一致。

镜像已包含功能修复，因此移除了充电、圆角、指纹属性、电话网络/短信和旧震动
HAL 的历史运行时交付钩子；保留其原文件用于恢复。诊断模块加载、blocklist、
CPU idle、ADB 和日志入口继续保留，不宣称已收敛为正式启动链。

## 首次启动后的结果

- 新 boot ID 为 `6b081ede-8bbd-4787-91e7-8b14603f8a3f`，B 槽，boot_completed=1。
- 震动 HAL 文件与受测二进制完全一致，不再依赖临时 bind；原厂 Tiktap HIDL
  为 disabled 且没有运行进程。冷启动未启动过的服务状态属性可以为空。
- 全部九项原语可查询；203 项真机控制检查通过，0 failures。
- framework THUD/SPIN scale=0.3 的低/中/高峰值仍为 29/37/46；关闭档无对应
  工作进程且记录 ignored_for_settings。工作进程上下文确认为
  `u:r:vendor_tiktap_worker:s0`，测试后恢复触觉开关/强度 1/3/3。
- 原第三方应用列表保留，旧功能交付挂载未残留；保留的诊断模块加载挂载摘要正确。
- deep 挂起模式、默认网络 33,33、QSPA enabled 正确；IMS、CNE、DPM 服务运行。
- Wi-Fi 自动重连，系统网络能力为 VALIDATED；电池信息正常，报告满电、协商 3 A。
- 用户已手动首次解锁，状态为 RUNNING_UNLOCKED，并反馈震动正常。原 10 个
  第三方应用均保留，对应加密应用目录均可访问；没有读取其私有内容，不能将
  目录存在等同于各应用业务数据完整验收。Wi-Fi 绑定 wlan0 的外网 ICMP 三发
  三收，零丢包，触觉设置仍为 1/3/3。
- 解锁后系统仍报告两卡 ABSENT，实卡是否在位待用户确认，尚不能进行蜂窝注册、
  实际通话与短信验收。已知 `slim_daemon` 的缺符号问题仍存在。

本轮未重新执行全部摄像、录音、指纹、蓝牙及长时间待机测试。全部场景触感、
高负载延迟、enforcing、CTS/VTS、长期功耗及正式 OTA 仍需独立验收。
原始日志、镜像、摘要、备份和操作记录在本地忽略目录
`.local-flash/full-system-20261119/`，不随 Git 分发。
