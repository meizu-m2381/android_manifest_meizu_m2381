# Recovery、OTA 与标准启动链

M2381 使用独立的 `recovery_a`/`recovery_b`，每个 100 MiB。Recovery 镜像只包含
ramdisk，内核由同槽 boot 提供；`vendor_boot` 同时提供常规启动与 recovery
所需的模块。不能把仅有 ramdisk 的 recovery 镜像当成独立内核镜像使用。

## 上游依据

- [LineageOS Xiaomi SM8550 板级配置](https://github.com/LineageOS/android_device_xiaomi_sm8550-common/blob/lineage-23.2/BoardConfigCommon.mk)：
  独立 recovery、`BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE`、
  `BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD` 与 OTA 分区列表。
- [456350](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/456350)：
  并行加载首阶段模块会导致 recovery 偶发无法启动，上游已撤回该开关。
- [478734](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/478734)
  与 [479217](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/479217)：
  recovery 需要 ADSP 模块、固件挂载与启动才能获得电池状态。
- [官方 recovery init](https://github.com/LineageOS/android_device_xiaomi_sm8550-common/blob/lineage-23.2/init/init.recovery.qcom.rc)：
  固件 fallback 仅在 recovery early-init 打开，不追加会拖慢正常触摸固件加载的全局内核参数。
- [473836](https://review.lineageos.org/c/LineageOS/android_device_samsung_sm8550-common/+/473836)：
  同平台改用源码 AIDL USB/Gadget HAL，并配套源码 USB init。

AOSP 的 [dynamic_partition_control_android.cpp](https://android.googlesource.com/platform/system/update_engine/+/refs/heads/main/aosp/dynamic_partition_control_android.cc)
在 recovery 中关闭 VABC；若不能创建 snapshot，完整 sideload 可回退为直接更新
逻辑分区。因此「recovery 完整包安装成功」与「Android 内 OTA 快照创建/合并成功」
需要分别验证，不能仅凭 recovery 安装后 snapshot=none 推断已测试合并。
官方 adb 的 sideload-auto-reboot 可用于自动化测试，但它在失败时也会重启；
仍必须核对客户端结果、实际槽位、镜像摘要和更新状态。

## 设备接入

`AB_OTA_PARTITIONS` 包含 recovery，移除 `TARGET_NO_RECOVERY` 和只为禁用 recovery
阶段保留的 `PRODUCT_BUILD_GENERIC_OTA_PACKAGE`。沿用原厂 DTBO，因此 OTA 不更新
dtbo 或 modem 等固件分区。

常规首阶段清单保持原厂 118 个模块；recovery 清单来自本机原厂 vendor_boot，
去重、应用现有 blocklist 后补齐六个 ADSP 依赖。Recovery 中的充电模块同样使用
已有 PD 兼容副本，避免回到未修复的原厂模块。

DTB 使用内核仓 `dtb/android/m2381.dtb`。它只禁用原厂 DT 内嵌的旧 vendor ext4
挂载规则，由现行 ramdisk fstab 决定 EROFS 和逻辑分区；原始 DTB 保留，兼容副本
可通过 `tools/prepare_android_dtb.py` 复现并检查摘要。

USB 使用官方 QTI AIDL 服务、配套源码 init 和 compositions。原厂 HIDL USB 服务、
对应 init/VINTF 声明、旧 USB init/script 及 compositions 共九项，由
`tools/configure_connectivity.py` 同时从产品选择、Make 模块定义及提取清单排除；
原始文件保留在 vendor 仓中。仅移除 PRODUCT_PACKAGES 不足以处理 Make 的全局
安装目标：未选中的原厂模块仍会覆盖同路径的源码规则，解包镜像检查已实际捕获
这个问题。旧 init 把 configfs 节点留给 root，源码 AIDL 服务以 system 用户
运行，会报告 `Gadget cannot be pulled down`，此前诊断脚本直接配置 ADB 绕过了它。

正常启动不应再有 `androidboot.init_rc=/metadata/bootdiag/...`、
`androidboot.first_stage_console`、`/first_stage.sh`，也不应出现来自 bootdiag 的
bind mount 或 CPU idle 诊断写入。Deep 挂起适配仍由设备 init 提供；已确认会
阻塞启动的 `tz_log_dlkm` 以及不属于 AOSP zram 栈的 `smartswap_zram` 保持 blocklist。

## 验证记录

2026-11-20 已完成模块输入检查（118/340 项，缺失和重复均为零）及 DTB 工具五项
检查：缺少输出拒绝、已知输入复现、复现结果核验、未知输入拒绝、未知已有输出保护。

`recoveryimage vendorbootimage bootimage initbootimage` 构建退出码为 0。解包镜像
确认 recovery 为 header v4、kernel_size=0；vendor_boot 的 DTB 摘要符合兼容副本，
普通/recovery 清单分别为 118/340 项，实际模块无缺失，充电模块与 PD 兼容副本
逐字节一致。通用 init_boot、vendor_boot 和 recovery ramdisk 中未发现诊断脚本
或 metadata bootdiag 引用，bootconfig 也不含诊断入口或并行模块加载开关。

已备份并核验 A/B 启动分区，在 B 槽写入新 boot、init_boot、vendor_boot、recovery，
沿用已有 flags=3 的 vbmeta。用户在官方界面 Advanced → Enable ADB 后，root ADB
连通；实际加载 340 个模块，电池为 100%，USB 控制器为 `a600000.dwc3`，
userdata 未挂载，无 bootdiag 挂载。默认安全认证显示 `unauthorized` 属于官方
recovery 行为，不需要关闭产品的 ADB 认证。

通过官方 recovery socket 进入 fastbootd，`is-userspace=yes`、B 槽和 super 名称
正确，recovery/逻辑 system 分区查询成功，snapshot 状态为 none。执行
`fastboot reboot recovery` 后在同一内核会话恢复 root ADB，电池读数仍正常。
这次单独测试不代表完整 OTA 或最终匹配 AVB 链验收。

Sideload 已实际传输仅含说明文字的未签名 ZIP。Recovery 报告签名验证失败，
用户选择 No 后安装状态为 2（拒绝），root ADB 恢复，四个受测启动分区摘要均未
改变。主机等待期间因人工确认耗时触发超时，不能将该次客户端命令记作成功安装。
编译期间曾恢复四个启动分区至原工作版本，待修正 USB 镜像通过审核后，已继续下述
标准启动链测试。

标准 B 槽启动已通过：使用构建生成的 boot、init_boot、vendor_boot、recovery、
匹配 vbmeta，以及新 vendor/vendor_dlkm；其余五个逻辑分区沿用前次完整安装。
完整 AVB 描述符/哈希树验证通过，七个刷入镜像的真机回读摘要一致。
boot_completed=1，首次解锁为 RUNNING_UNLOCKED，原十个第三方应用和 userdata UUID
保留。bootconfig 无诊断参数，挂载表无 bootdiag；UDC 为 system:usb 所有，两个
源码 AIDL USB 服务运行，framework 报告 USB HAL 2.0 和 CONFIGURED。
八个 CPU 的 state1/disable 均为 0，mem_sleep 为 s2idle [deep]。
ADB root 通过系统原有「Root 调试」开关启用，无需诊断脚本强制运行。
固件同步后再次正常启动；随后把旧 `/metadata/bootdiag` 同文件系统改名为
`/metadata/bootdiag.disabled-20261120` 保留，再次重启完成。原诊断路径确实不存在，
bootconfig 和挂载表仍无诊断引用，USB 服务正常；无需删除备份来证明解除依赖。

Recovery 界面、USB ADB、电池、fastbootd 与上述标准启动已完成真机检查。解除 CPU idle 限制后的拔线熄屏短测
新增 8 次成功挂起、2 次 freeze 阶段中止；boot ID 未变且 pstore 为空，详见
[待机路径](suspend-adaptation.md)。
USB 通过 framework 的 svc usb 依次切换 MTP、PTP、仅 ADB，均实际
CONFIGURED、保留有线 ADB，boot ID 未变，最后恢复原始配置。
完整 `pixelos` 目标已在 WSL 使用 Siso 完成，退出码 0，178,830 项任务；
API/ABI、apex_sepolicy_tests 和 host_apex_verifier 等构建检查通过。
首个候选包为 `PixelOS_m2381-17.0-20261119-1854.zip`，3,474,951,279 字节，
SHA-256 为 `03eda347d2af356c6f2e98af2aeb5fc2dcafdc0b901556ad32943826026d104c`。
最终 target_files 的 13 个分区与 payload 一致，官方 ota_extractor 提取回读
13/13 通过；ZIP CRC、payload 流式哈希、metadata 哈希、AVB 全链及主机整包和
payload 签名检查均通过。再次解包 OTA 提取的 ramdisk/vendor，确认源码 USB
三文件、AIDL VINTF、118/340 模块、DTB 与 PD 模块正确，无诊断入口。
这是已有产物的增量构建；源代码归档缺少 repo 元数据，仅生成的构建报告规则
复用明确不完整的 archive manifest，不宣称全新同步或完整来源锁定。
SELinux permissive 与设备完整 enforcing 验收是独立
事项，不能由 OTA 成功推断。

### 完整安装与真实快照合并

上述完整包已从标准 B 槽执行官方 `adb reboot sideload-auto-reboot` 和 sideload。
主机退出码 0、total xfer 1.00x；手机实际启动 A 槽，boot_completed=1，13 个分区
按 payload 实际字节数回读 SHA-256 全部一致。userdata UUID 与原十个第三方
应用列表保留，原 `/metadata/bootdiag` 不存在，无诊断参数或挂载，源码 USB 服务正常。
当前内核无 `/dev/pmsg0`，未取得重启后持久化 recovery 安装日志；未将自动重启
本身当成安装成功证据。Recovery 安装后的 snapshot=none 也不作为合并证据。

随后从 A 槽通过官方源码构建的 `update_engine_client --update --follow` 应用同一
完整 payload：未改时间戳、未清除数据、未手动标记槽位成功。客户端返回 kSuccess，
更新后真实 snapshot 为 unverified，snapuserd/userspace snapshots 均为 1，B 被选为
活动槽。重启后实际进入 B，观察到 merging，再通过官方 `--merge` 等待清理成功，
最终 snapshot 和 BootControl merge status 均为 none。B 自动标记 successful，
13 个分区回读再次全部匹配；userdata UUID、十个应用列表、源码 USB、deep 模式及
八个 CPU state1/disable=0 均保留。原始证据分别为
`recovery-full-ota-result.json`、`android-full-ota-result.json` 和 merge 日志。

完整包首次启动暴露了媒体兼容问题：64 位 codec2 缺少旧 GraphicBufferMapper::lock，
而此前仅 32 位配置了官方 libui shim。现将同一
[394610](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/394610)
shim 扩展到 64 位，固定原始/修补摘要，完整包重建及重新安装验证单独记录。
另有一次音频 `stringToAudioSource` 崩溃及相机服务查询造成的启动 watchdog 延迟。
原厂/源码音频枚举各 8,000 次转换和现装系统 15 次输入流打开/释放均通过（未开始
录音），暂未据此替换音频库。不能用历史摄像、录音、通话结果覆盖本次完整包回归。
用户夜间未首次解锁，状态为 RUNNING_LOCKED；应用私有加密数据和全部交互功能
需要解锁后重新验收。重启后读取到一份内容损坏的旧 console-ramoops，不能据此
推断本次 kernel panic，也不能报告 pstore 为空；当前 boot reason 为 reboot,shell。

### 最终修正包与复验

最终受测包是 `PixelOS_m2381-17.0-20261119-2333.zip`，3,474,917,783 字节，
SHA-256 为 `9211bad97d1665a7c1c2bca0ebaa8207197995e0c0f1829751abd3c10b94bc80`。
完整 `pixelos` 增量构建退出码 0，Siso 实际执行 196 项、用时约 6 分钟。
ZIP CRC、metadata/payload 哈希、整包与 payload 签名、13/13 官方提取回读及完整 AVB
链通过。重新解包确认 USB、118/340 模块、DTB、PD 模块和无诊断入口；全部 18 项
固定摘要兼容副本正确，两种架构的 libui shim 均导出所需旧 mapper 符号。
六项兼容输入回归用例实际运行通过，没有跳过。

对这个修正包重新完成两条安装路径：Recovery B→A 完整安装后 13 分区回读匹配；
Android update_engine A→B 再次创建真实 userspace snapshots，重启后 merging→none，
官方 merge 回调成功、B 自动 successful，13 分区回读再次匹配。未手动标记成功、
未取消或重置快照、未清除用户数据。两次均保留 userdata UUID 与十个第三方应用列表。

Recovery 安装后、Android OTA 合并后和额外普通重启后，分别执行两种架构的
C2/OMX 硬件 AVC 编码：每项输出 10 帧及 EOS；各完成 15 次音频输入流打开/释放，
未开始录音或播放声音。音频、视频 codec、音频 codec 服务 PID 在受测窗口保持稳定，
不再出现旧 GraphicBufferMapper 缺符号。额外普通重启约 25 秒到 boot_completed，
无新增 ANR/tombstone；B successful、snapshot none、USB CONFIGURED、deep 及八个
CPU state1/disable=0 正常，原诊断目录仍不存在。初版音频崩溃/相机查询延迟未在
这些修正版启动中复现，不能由短测认定长期问题完全消失。

最终结果在本地 `media-final/` 下的 `recovery-full-ota-result.json`、
`android-full-ota-result.json`、三份 `*-media-runtime.json` 和
`normal-reboot-result.json`。手机最终为 B 槽正常系统；首次解锁、应用加密数据、
摄像实拍、实际通话和长时待机仍需用户参与或后续独立验收。没有把这些历史功能
测试或本次无声编码测试当成完整硬件验收。
结束时已删除手机上的临时 OTA ZIP、辅助 bootctl/update_engine_client 和本轮探针，
确认同一 boot ID 下系统、媒体与 USB 服务继续正常；本地镜像/日志/分区备份及
改名保留的旧诊断目录未删除。

跨槽预检发现 23 组固件中有 19 组 A/B 摘要不同。已阅读 LineageOS 官方
[固件一致性模板](https://github.com/LineageOS/lineage_wiki/blob/main/_includes/templates/device_specific/before_lineage_install_ab_copy_partitions.md)
及其 copy-partitions-20261011-signed.zip 实际脚本。脚本枚举活动槽，排除 boot、
init_boot、vendor_boot、vbmeta 等；本机预计涉及 29 组（含 recovery），已对全部
58 个源/目标分区备份并核验摘要，随后通过 recovery 正式 sideload 执行官方包。
官方镜像目录公布的 SHA-256 与下载一致，主机整包签名检查通过；设备 recovery
报告 whole-file signature verified against RSA key 0，安装状态为 0。复制后
29 组 A/B 摘要逐一一致，B 槽源内容及全部排除项保持原样，userdata 未挂载。
DTBO 被该脚本排除；本机硬件使用
第 9 项，该项 A/B 完全相同，整包差异只在未使用的第 0 项。
该同步是本机跨槽测试的一次性前置操作，未把固件写入 ROM OTA payload。

原始日志、镜像和分区备份保存在工作区外层的
`.local-flash/recovery-ota-20261120/`，不随 Git 分发。
