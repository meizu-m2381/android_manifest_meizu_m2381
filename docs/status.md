# 功能状态（2026-11-20）

当前受测系统为 PixelOS 17 / Android 17，使用官方 shim 和设备兼容副本。
公共 AOSP、Aperture、CameraX 与冻结 VNDK 不需要设备专属源码修改。
以下区分已执行的检查与尚未完成的验收；原始照片、日志和分区备份不随仓库分发。

| 功能 | 已有验证 | 尚未覆盖 |
| --- | --- | --- |
| 启动/桌面 | 完整 pixelos 增量目标仍在重建；标准 B 槽启动链已安装 boot/init_boot/vendor_boot/recovery、vendor/vendor_dlkm 与匹配 vbmeta，boot_completed=1，bootconfig 无诊断入口，7 个镜像回读摘要一致；原 10 个第三方应用与 userdata UUID 保留，USB AIDL HAL 2.0 的 MTP/PTP/ADB 切换通过；见 [Recovery/OTA](recovery-ota.md) | 完整 OTA 包、跨槽升级合并、长时功耗 |
| 图形 | ARM/ARM64 GLES 2.0–3.2 像素绘制、Chrome 启动；圆角已目视校准 | 长时间游戏、压力与所有应用兼容性 |
| Wi-Fi/蓝牙 | Wi-Fi 联网与重启重连；蓝牙开启，历史版本验证过文件接收 | 本版蓝牙耳机/通话、吞吐与功耗 |
| 三摄照片 | 主摄、超广角、前摄 JPEG 完整解码，正常场景有细节，预览 AE 收敛 | 长时间使用与全部拍摄模式 |
| 录像 | 三摄各 720p/1080p/4K 请求 60 fps；短测约 59–60/59–60/58 fps；Aperture 档位经用户确认 | Aperture 自身录像逐帧统计、长录像热稳定性 |
| 音频/媒体 | 麦克风 PCM 非零、录像含音轨、硬件 AVC 解码通过；外放程序完成播放，用户随后自测反馈正常；普通通话双向声音经用户确认 | 全部音频路由、蓝牙音频和蓝牙/免提通话 |
| 充电 | Health 单位/估时/状态与快充分类修正；电脑 PD 连接重启四次实际取电，电源切换未复现零限流 | 低电量大功率快充、SDP/CDP、长期温控 |
| 待机 | deep 路径历史 28 次成功挂起；标准启动解除 CPU idle 诊断限制后，拔线熄屏短测新增 8 次成功、2 次冻结阶段中止，boot ID 未变、pstore 为空 | s2idle 底层阻塞根因、长时功耗与全部唤醒场景 |
| 指纹 | 原厂位置修正，用户确认录入与锁屏解锁成功 | 支付/应用认证、多模板与长期待机 |
| 震动 | 镜像已包含原厂 RAM 预设和全部九项组合原语，完整安装重启后 203 项控制检查通过；framework 低/中/高/关闭通过，工作进程独立域已确认；用户解锁后反馈震动正常，见 [组合记录](tiktap-trial.md) | 全部应用场景、长时功耗、enforcing 模式、CTS/VTS 与无诊断依赖安装 |
| 移动网络 | 联通 NR SA 和 LTE 实际数据联网，关闭 Wi-Fi 后 HTTP/ICMP 通过；默认模式与旧订阅策略修复，NR 信号刻度校准，DPM 官方 shim 真机启动；补齐原厂 IMS/QTI 音频桥及 QSPA 标记，CNE 签名权限恢复，用户确认实际接通和双方声音正常；QCRIL 开机优化修复后积压普通短信已投递信息应用，重启自动加载兼容库 | 短信长期收发、双卡、其他运营商、主动视频通话、VoLTE/VoNR 切换与长时稳定性 |
| RCS | 已补齐同机原厂 RCS 服务与 14 个 Java HAL 库，系统成功绑定，配置接口返回 OK；完整 ICCID 框架试验消除了移动标识无效提示，但未开通，试验已回退 | 单注册 SIP transport 返回 NOT_SUPPORTED；两卡 Google 信息仍缺 RCS 配置并报告 UNSUPPORTED_BY_CARRIER，注册与真实 RCS 收发均未通过 |
| GNSS/NFC | 保留服务和固定厂商输入 | 完整硬件验收 |

## 仍存在的问题

- `slim_daemon` 缺 `__emutls_get_address` 仍待处理。`vendor.dpmd` 原来缺失的
  `android::hardware::Parcel::setData` 已复用官方 shim 修复并验证启动，长时稳定性
  仍需观察，详见 [移动网络适配](mobile-network.md)。
- 标准启动链已移除诊断 ramdisk、metadata 入口和 CPU idle 限制；跨槽固件已通过官方包同步并回读，完整 OTA
  与合并仍待完成。SELinux 仍为 permissive，enforcing、CTS/VTS 尚未验收。
- `DIGITAL_CLOCK_NUMBEROVERLAP` 锁屏日期有越过屏幕右边缘的已知布局问题。
- 标准启动链和 recovery 负向签名检查已通过；正式 recovery/OTA 安装和跨槽合并
  仍需完成。全新同步后的干净构建尚未覆盖。首次启动时用户未插卡，随后
  插卡后移动、联通均已加载并注册 NR SA；本次移动数据开关关闭，未重测实际
  蜂窝流量、通话和短信。

当前是适配开发版本。LineageOS 产品已注册并做基础解析，尚未在独立 LineageOS
源码树完整编译和启动；其他衍生 ROM 同样需要独立验收，见 [复用范围](rom-compatibility.md)。
