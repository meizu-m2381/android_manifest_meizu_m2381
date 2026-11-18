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

已基于现有构建暂存目录定向重打包 vendor 镜像，并完整提取检查 EROFS 内容：
DPM 兼容副本和官方 shim 的 SHA-256 均与受测文件一致，镜像内默认属性为
`33,33`。`avbtool verify_image` 通过 footer 和 SHA-256 hashtree 检查；该镜像
的 vbmeta 算法为 `NONE`，此结果不代表签名信任链通过。该镜像未刷入手机，
本次也未执行全量干净构建或正式 OTA 验收。

双卡、其他运营商、实际语音/短信、VoLTE/VoNR、跨小区移动和长时间稳定性需要
独立验收。默认网络属性只为未保存用户配置的订阅提供初值，不强制重写用户
后续选择。
