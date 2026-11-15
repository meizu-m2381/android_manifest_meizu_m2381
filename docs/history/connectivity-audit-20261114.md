> 历史核查记录（已去除启动标识）。以 当前状态（原工作区：`../status.md`） 为准；文中日志和截图留在原本地工作区，未随本仓库发布。不是刷机指南。

# Wi-Fi 与蓝牙修复记录（2026-11-14）

设备为 MEIZU 20，现有 PixelOS 第四十七组启动链。用户要求优先修复 Wi-Fi、蓝牙，充电问题留待再次复现。原始日志、附近网络、配对信息与镜像均留在本地忽略目录，不提交设备转储。

## 定位到的三个问题

1. **Wi-Fi HAL 声明与实际运行服务冲突，底层库也存在 ABI 覆盖。** 原厂 HIDL 1.6 manifest 与源码 AIDL v3 manifest 同时安装，两个 rc 使用同一个 `vendor.wifi_hal_legacy` 服务名，实际运行源码 AIDL。`packages/modules/Wifi/service/java/com/android/server/wifi/hal/WifiHal.java` 优先选择已声明的 HIDL，因此反复等待不存在的旧服务。`dumpsys wifi` 最初只返回服务未启动。内核已创建 wlan0/p2p0/wifi-aware0。移除旧声明后，进一步通过实机崩溃栈定位原厂 `libwifi-hal.so` 的函数表布局不兼容，最终也改用同源编译产物。
2. **原厂连接程序覆盖源码产物，且加密库 ABI 不兼容。** 手动启动旧 HIDL 服务后，框架完成初始化，但原厂 `wpa_supplicant` 反复因 `sk_dup` 缺失退出。临时绑定已编译的源码 AIDL supplicant 后成功扫描并连接网络。旧 hostapd 同样覆盖源码安装路径，统一撤下对应预编译程序、rc 和 manifest，由源码模块提供。
3. **蓝牙的依赖服务先于控制器初始化失败。** 系统蓝牙在 HIDL `initializationComplete` 收到失败后主动 abort，开机七次崩溃。对原厂蓝牙 HAL 的 strace 记录到连接 `/dev/socket/ssgtzd` 返回 ENOENT，随后 `Failed to register BT peripheral with TZ`。`ssgtzd` 因 VNDK33 libssl 与当前 vendor libcrypto 混用、缺少 `CBS_init` 而不能启动。临时使用匹配的 VNDK33 crypto 启动 daemon 后，蓝牙成功进入 ON，正常初始化控制器。临时 bind 随后已解除。

## 信号图标偏低

用户连接成功后反馈路由器就在附近、图标仍偏低。实测 5GHz 连接，RSSI 约 -49dBm，驱动双天线平均约 -49/-50dBm，接收协商速率约 585–650Mbps、VHT NSS 2。SystemUI 同时记录 `rssi=-49, level=2`。

`cmd overlay lookup --verbose` 指向原厂 `WifiResCommon_Vendor_Mz.apk` 的 `config_wifiRssiLevelThresholds=[-77,-63]`，数组只有两个阈值，所以框架最高只返回 2；PixelOS 图标使用 0–4 级。它足以解释强信号也显示两级，不能据此判断天线失效。

改为源码 `WifiOverlayM2381`，阈值恢复 AOSP 的 `[-88,-77,-66,-55]`，强于 -55dBm 对应 4/4，弱信号仍按实际 RSSI 降档。保留原厂覆盖中的扫描周期、字符集、热点能力与连接阈值等硬件/策略参数；没有提高发射功率、改射频校准或写入 persist。原厂 Flyme UI 专用的 `wifi_item_content` 样式没有移植。

## 构建配置修改

- `tools/configure_connectivity.py` 移除指定原厂模块的生成安装规则，保留本地原始输入；重复执行不再修改文件。`tools/blob_exclude.txt` 防止重新提取时恢复这些覆盖规则。构建脚本同步后也执行该清理。
- Wi-Fi HAL、libwifi-hal、supplicant、hostapd 由现有源码模块提供，删除与之冲突的旧 HIDL 声明和原厂 supplicant 扩展声明。共排除 12 个旧安装条目。
- 设备树维护 `ssgtzd.rc`，只给这个 API 33 daemon 设置 `LD_LIBRARY_PATH=/apex/com.android.vndk.v33/lib64`，让它的 libcurl/libssl/libcrypto 使用匹配的 ABI。其他源码服务继续使用当前 vendor 库。`linker64 --list` 已确认这一路径会解析到匹配的库。
- 原厂 Wi-Fi 公共资源 APK 改为源码 RRO，修复信号分级。
- `tools/prepare_vendor_update.py` 以完整、摘要校验过的旧候选准备 vendor 更新，重新生成 top vbmeta 并验证完整 AVB 链；boot/init_boot/vendor_boot/vbmeta_system 保持逐字节不变，诊断 init 路径不变。

## 已执行验证与边界

临时验证阶段：蓝牙进入 ON 并持续运行十余分钟；Wi-Fi 扫描到 2.4GHz/5GHz 网络，用户手动连接成功，获取 IPv4 地址、网络 VALIDATED。绑定 wlan0 测试路由器 5/5、外网 IP 3/3 均成功，无丢包。源码 supplicant 正常注册 AIDL v4。此时 Wi-Fi 主 HAL 仍是手动启动的原厂 HIDL，仅用于定位，不能当作最终 AIDL 配置已验证。

vendorimage 已编译通过，实际 EROFS 拆包确认旧 Wi-Fi HAL 程序/rc/manifest 消失，supplicant 与 hostapd 与源码产物逐字节相同；ssgtzd rc 的 init verifier 通过，震动服务摘要保持第四十七组的已验证版本。复制路径冲突检查为零，Python 与构建 shell 语法检查通过。最终运行及普通重启结果见下文。

## 首次刷入发现的追加问题

包含信号 RRO 的第一版镜像编译、完整 AVB 和刷写均通过；系统内实际读取六个分区 SHA256 全部匹配候选。蓝牙自动进入 ON、崩溃计数为 0，保留用户已确认成功的一个配对记录。`ssgtzd` 实际映射的 libssl/libcrypto 来自 VNDK33 APEX，证明进程级修复生效。信号阈值实际解析到源码 RRO 的四个阈值。

但首次恢复候选的脚本遗漏了退出 recovery 前清除 BCB 命令，导致停留 Meizu 标志。用户进入 fastboot 后，执行一次 `fastboot continue` 成功进入系统；实际读取命令为 `boot-recovery`。保存 misc 前 2048 字节后只清前 32 字节，并验证剩余字节完全一致。这是刷写流程遗漏，不能误报为网络镜像启动失败。

最终 AIDL 验证进一步发现旧 `vendor/lib64/libwifi-hal.so` 仍覆盖同名源码库。崩溃栈显示 `getLoggerSupportedFeatureSet` 实际跳进原厂 `wifi_get_tdls_status`，把整数当指针写入地址 0x5；这是旧 `wifi_hal_fn` 表布局与当前头文件不匹配。将这个库临时绑定为同源编译产物后，HAL 不再崩溃，重新启用 Wi-Fi 即连接已保存的网络并获得 VALIDATED，RSSI 约 -47dBm。随后将该库纳入源码所有权排除规则并完成下列持久验证。

## 最终持久版本与普通重启验证

第二版 vendorimage 构建耗时 5 分 6 秒并成功。实际 EROFS 与第一版逐文件比较，仅 `lib64/libwifi-hal.so` 内容变化；它与临时验证通过的源码库 SHA256 相同：`cb2bf90d219ae3cc3311360678b383c5da3237c23c316de90377cce5161a7367`。单一 AIDL HAL、源码 supplicant/hostapd、信号 RRO、蓝牙 rc 和原有震动版本均保留。完整 AVB 校验和主机六镜像摘要通过。

解除临时 bind，按完整原厂启动链进入诊断 recovery；归档本轮日志并逐项核对设备/主机摘要后，仅删除已核对的旧日志，metadata 可用 9468KiB，十个诊断输入摘要保持。经原厂 recovery/fastbootd 写入 B 槽 vendor，恢复诊断 recovery 并在退出前备份、清除 BCB 前 32 字节命令，核对剩余 2016 字节不变，再恢复候选启动链。系统成功启动，六个实际分区 SHA256 全部匹配第二版清单。

随后执行一次普通 `adb reboot`，18.59 秒完成开机且 boot_id 改变。未手动启动 HAL、未挂载临时库、未重新输入网络密码，实测：

- Wi-Fi 自动连接保存的 5GHz 网络，supplicant 状态 COMPLETED，网络 VALIDATED；框架使用 AIDL HAL，启动日志无旧 `sk_dup` 错误或 Wi-Fi SIGSEGV。
- 绑定 wlan0 测试路由器 5/5、外网 IP 3/3 成功，均无丢包。这只验证连通性，不是吞吐量测速。
- 源码信号 RRO 实际生效，SystemUI 在当前强信号下为 level=4；唤醒截图显示完整信号图标。
- 蓝牙自动 ON、崩溃计数为 0；重启前用户已确认双方配对成功，重启后保留 1 个配对记录。`ssgtzd` 实际映射 VNDK33 的 libssl/libcrypto，未出现 `CBS_init` 缺符号错误。
- misc 启动命令保持空白；震动服务自动运行，已验证 binary 摘要及默认增益保留；启动诊断 deadline 已停止。

证据保存在本地 `logs/connectivity-audit-20261114/`：`vendor-v2-content-diff.json`、`restore-candidate-v2-log.txt`、`flashed-partition-verification-v2.json`、两次 recovery BCB 快照，以及 `postflash-v2/`、`postreboot-v2/` 的运行日志、库映射、连通性和截图。

本轮验收覆盖 Wi-Fi 扫描/连接/自动重连、信号显示、蓝牙初始化与配对记录保留；未验证蓝牙耳机音频、实际文件传输、Wi-Fi 热点、多设备并发或长时间待机稳定性。没有擦除 userdata/metadata、改动固件或射频校准；SELinux 仍沿用当前诊断版本的 permissive，未作为发布版安全验收。

## 手机间连接状态与文件接收补测

用户反馈另一台手机配对成功后显示“未连接”。本机记录确认重新配对认证成功，随后因 `All channels closed` 关闭空闲 ACL；没有持续使用的 profile 时，配对成功不等于持续保持连接。日志也保留了一次旧配对 `KEY_MISSING`，不能将该次认证失败混为后续重新配对仍失败；重新配对已成功。

用户随后从另一台手机通过蓝牙发送文件，确认魅族接收成功。本机 OPP 记录为 `direction=1, status=200, total_bytes=72870, current_bytes=72870`，证明实际收到完整 72870 字节，补齐接收方向的数据传输验证。未读取文件内容，文件名与配对地址不写入本文；反向发送、耳机音频及其他 profile 仍未验证。证据位于 `bt-phone-link/opp-transfer-status.txt` 和 `transfer-evidence.txt`。

后续观察中 Wi-Fi 连接与数据链路保持，但系统网络验证由 VALIDATED 转为 PARTIAL_CONNECTIVITY：HTTP 探测返回 204，Google HTTPS 探测目标超时，日志中的 DNS 结果包含异常的 Google 地址。此前短时 VALIDATED 不能表述为所有外网服务持续可达；本轮未改动网络探测地址或 DNS 策略。
