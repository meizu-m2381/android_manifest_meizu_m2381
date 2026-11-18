# 移动网络适配

修复位于设备属性、设备 CarrierConfig RRO 和 vendor 兼容副本中，不修改公共 AOSP、
LineageOS compat 或冻结 VNDK 源码。

## 默认网络模式

设备原来没有设置 `ro.telephony.default_network`。Android 的
`RILConstants.PREFERRED_NETWORK_MODE` 在该属性缺失时回退到 `WCDMA_PREF`，
本机新建订阅实际只允许 GSM/WCDMA，未启用 LTE/NR。受测联通卡停留在 UMTS
拒绝注册状态，数据连接显示 `SERVICE_OPTION_NOT_SUPPORTED`。

设备 `configs/properties/vendor.prop` 增加 `ro.telephony.default_network=33,33`，
让两个卡槽默认采用包含 NR/LTE 的自动模式。相同平台的
[LineageOS 官方配置](https://github.com/LineageOS/android_device_oneplus_sm8550-common/blob/lineage-23.2/properties/vendor.prop)
采用同一属性。已有订阅保存的用户选网设置不会被只读属性覆盖，需要在设置中
重新选择 5G/4G 自动模式；本机已通过 Telephony shell 接口修复现有订阅。

本机旧订阅还保存了不包含 LTE 的 `power` 原因掩码。只调整 `user` 原因可以
连接 NR SA，但切换 LTE 时两类掩码交集为空，接口会返回失败。已通过现有
`ITelephony.setAllowedNetworkTypesForReason` 给该订阅的 `POWER` 原因补回
LTE/LTE_CA，保留其余位；不能直接修改数据库后将其误称为基带接受了配置。

## DPM 旧 HIDL 接口

原厂 `vendor.libdpmframework.so` 依赖已移除的
`android::hardware::Parcel::setData`，导致 `vendor.dpmd` 持续链接失败。
复用已合并的官方 [401141](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/401141)
提供的 `libhidlbase_shim`。同平台官方
[提取配置](https://github.com/LineageOS/android_device_oneplus_sm8550-common/blob/lineage-23.2/extract-files.py)
对同名 DPM 库使用 `.add_needed('libhidlbase_shim.so')`。

设备产品显式打包 64 位官方 shim；`configs/compat/libbase-fixups.json` 固定原厂和
修补后摘要，通过现有工具生成 `compat/vendor/lib64/vendor.libdpmframework.so`，
仅切换这一库的安装来源，保留 `proprietary/` 原始输入。

## 5G 信号格数

本机 NR SS-RSRP 约 `-88 dBm` 时显示两格，实际使用通用阈值
`[-110, -90, -80, -65]`，格数与当前 LTE 的运营商刻度不同。
官方 [512834](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/512834)
采用设备 CarrierConfig RRO 将 NR 与原厂 LTE 的 RSRP 刻度对齐。

本设备只为受测的联通 `46001` 配置 NR 阈值 `[-120, -118, -114, -105]`，
复用已从魅族原厂 CarrierConfig 提取的该运营商 LTE 阈值。没有照搬 OnePlus
提交中的数值，也没有开启 `inflate_signal_strength_bool`。这是格数刻度校准，
不改变基带测量值或实际射频能力；未声称这些数值是原厂 NR 阈值。

## 拨号失败与 IMS 缺失

首次通话复测以 `Radio internal error, OUT_OF_SERVICE` 断开。拨号应用本身没有
Java 崩溃，系统未重启；同一时间共享网络进程 `.qtidataservices` 因
`NetworkCallback was not registered` 崩溃。此结果说明数据联网验收不能代替
语音验收。

CneApp 在申请受限网络时捕获了 `SecurityException`，随后清理时无条件注销
回调。原打包规则将原厂签名 APK 当作 `ETC` 复制，实际未获得
`CONNECTIVITY_USE_RESTRICTED_NETWORKS` 等签名权限。参照官方
[extract-utils 默认签名规则](https://github.com/LineageOS/android_tools_extract-utils/blob/lineage-23.2/extract_utils/bp_builder.py)，
改用 `APPS` 导入和当前系统 platform 证书；同一共享 UID 的 CneApp、
CACertService、IWlanService 一起签名，产品不再选择它们的原厂 odex/vdex。
不通过修改 ConnectivityManager 掩盖应用异常，也不修改原始 APK 代码。

另一个独立问题是设备 RRO 指定了 `org.codeaurora.ims`，但产品完全没有安装
该包，电话服务持续报告无可用 IMS 服务。参照同平台官方
[400053](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/400053)
接入 system_ext 侧 MMTEL 栈的方法，从本机原厂 super 备份提取匹配的 IMS、
QCRIL 消息通道、电话音频桥及配套库，共 18 项原始输入，固定大小和 SHA-256。其中 diag AIDL
库原位于原厂 system 分区，本设备随 IMS 安装到 system_ext；清单保留原厂路径。
APK 使用
platform 证书，JNI 库同时安装到 IMS 应用本地库目录；保留设备现有的源码
`ims-ext-common` 和 QTI telephony 公共库。未使用其他机型的 APK 或厂商框架。

原厂两个 APK 的 manifest 还带有 `ro.boot.vendor.qspa.modem=enabled` 条件。
缺少此标记时，包管理器会直接跳过这两个包，不能只凭文件已安装就认为 IMS
可用。官方同平台 [432193](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/432193)
启用 QSPA HAL，本设备已包含该 HAL；M2381 的旧 bootloader 没有提供上述标记，
设备 `init.m2381.rc` 在 `early-init` 为物理 modem 设置标记。原始 APK 不做
manifest/DEX 修补，AOSP 的解析器、电话框架和网络框架保持原样。

WSL 中 23 个 IMS/CNE 安装目标和设备 init 目标已编译通过。
6 个 APK 的证书与受测系统 platform 一致，DEX 与原始输入逐项相同；5436 项
构建输入和 5476 项随附输入校验均为 0 errors。通过现有诊断入口部署并重启后，两个 IMS 包已被
扫描，`org.codeaurora.ims` 与电话服务成功绑定，联通卡报告
`isImsRegistered=true`、`Voice: true`、`SMS: true`，CNE 的三项受限网络权限
均已授予。观察窗口未再出现 CNE 回调注销异常，IMS、CNE 和 DPM 进程保持运行。
首次拨号复测已接通约 26 秒，正常由对端结束，未重现原回调注销异常或基带
内部错误；但用户确认双向无声，不能据此将通话标为通过。音频 HAL 虽已进入
通话模式，两个语音会话仍为 `CALL_INACTIVE`。对照官方同平台
[预编译清单](https://github.com/LineageOS/android_device_oneplus_sm8550-common/blob/lineage-23.2/proprietary-files.txt)
补齐同机 `QtiTelephonyService.apk`：其 `QcRilAudioAidl` 连接基带的音频控制接口，
通过 `AudioManager.setParameters` 转发 VSID/通话状态；仅设置通话模式不能
代替该状态桥。

补齐音频桥后，基带的 `vsid`、`call_state=2` 和 `call_type=NR5G` 已传入音频
HAL，语音会话转为激活。用户实际拨号确认双方声音正常，原秒挂和双向无声
未再复现；接通后的电话状态为 `ACTIVE`、`Audio Only`。响铃阶段的接收视频
会话已由用户确认是实际的视频彩铃，不能仅凭拨号器的视频文案判定普通语音
被错误发起为视频电话。最终保留既有运营商视频配置；主动视频通话仍未验收。

最终恢复原有 CarrierConfig 后再次整机重启：23 个 IMS/CNE 运行文件摘要全部
匹配，IMS 重新注册，IMS、QTI 音频桥、CNE 和 DPM 进程稳定。绑定蜂窝接口
进行 HTTP 请求获得响应，ICMP 三发三收；NR SS-RSRP 为 `-86 dBm` 时为 4 格。
崩溃缓冲区未见 CNE/IMS 新异常，已知 `slim_daemon` 链接错误仍单独待处理。

## 验证边界

已在本机恢复联通 NR SA 注册和数据连接。关闭 Wi-Fi 后网页返回 HTTP 204/200；
绑定实际蜂窝接口访问公网并收到响应，ICMP 三发三收。LTE 单独选网也完成真实
蜂窝接口的 HTTP 响应及三发三收；最终自动模式恢复 NR SA。测试同时区分现有 VPN
路径与直接绑定蜂窝接口的路径。兼容工具的五项真实 ELF 回归通过，未跳过用例。

修复后的官方 shim 和 RRO 已通过 WSL 构建并在真机部署。DPM 重启后保持运行；
加载新 CarrierConfig 后，本机 `-93 dBm` 的 NR 信号计算为 4 格。再次整机重启后，
默认属性仍为 `33,33`，NR SA 数据已连接，DPM 保持运行；`-92 dBm` 的主信号仍为
4 格，崩溃缓冲区未见 DPM 链接错误。验证时还需注意
CarrierConfig 磁盘缓存：静态 RRO 不能用普通 APK 更新安装；更换系统内 RRO 后
旧缓存可能继续生效，应保存后清理对应包的派生缓存并重新加载电话服务。

当前手机仍沿用已存在的诊断启动链。本次用可回退的诊断 init 入口设置旧镜像
缺失的默认属性，在数据解密完成后的 `zygote-start` 阶段挂载校验过的 DPM 副本
和设备 RRO。原厂分区输入未改写；这项运行时部署不能代替正式镜像/OTA 安装
验收。普通构建通过设备属性、官方模块和 vendor 安装规则包含修复，不需要该
诊断入口。

本轮 IMS/CNE 同样通过诊断入口校验摘要后叠加只读目录，没有刷写分区。回退
时恢复部署前的 `init.round48.before-call.rc` 并重启，可移除 IMS/CNE 挂载与
本轮 QSPA 标记；本地部署文件和详细日志保留于工作区忽略目录，不随 Git 提交。

已基于现有构建暂存目录定向重打包 vendor 镜像，并完整提取检查 EROFS 内容：
DPM 兼容副本和官方 shim 的 SHA-256 均与受测文件一致，镜像内默认属性为
`33,33`。`avbtool verify_image` 通过 footer 和 SHA-256 hashtree 检查；该镜像
的 vbmeta 算法为 `NONE`，此结果不代表签名信任链通过。该镜像未刷入手机，
本次也未执行全量干净构建或正式 OTA 验收。

双卡、其他运营商、实际短信、主动视频通话、VoLTE/VoNR 切换、跨小区移动和
长时间稳定性需要独立验收。默认网络属性只为未保存用户配置的订阅提供初值，不强制重写用户
后续选择。
