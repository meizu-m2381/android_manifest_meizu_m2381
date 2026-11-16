# PixelOS 17 升级

> 2026-11-16 平台隔离迁移：下文的平台补丁和 remove-project 描述是历史构建记录。当前 Android 17 使用官方 shim、设备 linker 配置、预编译内核头接口与产品级源码选择，不再应用六项平台补丁或全局移除 HAL 项目。操作与验证边界见 [平台隔离](platform-isolation.md)。


`pixelos-17` 分支用于将 M2381 从 PixelOS 16.2 迁移到 PixelOS 17.0。完整构建、离线镜像校验、保留数据的真机升级和基本回归已通过；仍是依赖诊断启动链的 bring-up 版本，未完成所有硬件验收。

## 上游基线

- PixelOS manifest 分支：`seventeen`。
- 本次检查的 manifest 提交：`29f6010bcd2bd4742502ea7ccee763c64f02a3c1`。
- 默认 AOSP 标签：`android-17.0.0_r1`。
- LineageOS 分支：`lineage-24.0`。
- PixelOS 自报版本：17.0；构建 release：`cp2a`。

manifest 固定版本不等于其中所有分支引用已锁定。本次同步成功后的 `repo manifest -r` 已保存在 `provenance/pixelos17/revisions.xml`，包含 1232 个项目的实际提交；原厂 API 33 厂商输入继续使用随附版本，没有因为 Android 大版本升级就更换未知驱动。

## 最小拉取

在独立源码目录执行：

```bash
repo init -u https://github.com/PixelOS-AOSP/android_manifest.git \
  -b seventeen --depth=1 --manifest-depth=1 \
  --partial-clone --clone-filter=blob:none \
  --git-lfs --no-clone-bundle --no-tags --platform=linux
mkdir -p .repo/local_manifests
cp /path/to/m2381/provenance/pixelos17/00-m2381-prebuilt-kernel.xml \
  .repo/local_manifests/
repo sync -c -j4 --no-clone-bundle --no-tags
repo manifest -r -o pixelos17-revisions.xml
```

该配置限制提交历史、分支和无用 Git 对象；完整源码检出及 GMS LFS 对象仍会占空间。`blob:none` 不会省掉实际构建所需文件。附带的本地清单现为空，不排除上游项目：实际 Soong 解析会全局引用 Trusty、Microdroid 的多套通用内核模块，即使本机使用原厂 5.15 内核也需要这些模块定义。因此最小拉取通过浅历史、对象过滤和当前分支实现，不再按手机内核版本删减项目。

已有未完成同步可直接续传。不要为减少磁盘占用删除 `.repo`，否则不能可靠更新、记录版本或区分本地修改。升级目录与旧版本共用硬链接时，任何本地修补都应采用临时文件替换或先解除硬链接，不能原地写穿其他备份。

`repo sync` 返回成功仍需核对 Git LFS 实体。本次接近打包阶段发现 GMS 仓库有八个文件仍是指针，包括 `com.google.android.gmssystem.prodvic.apex`、WebView 和若干 Google 应用，导致 APEX 解包报 `BadZipFile`。在 `vendor/pixel/gms` 执行针对当前提交的 `git lfs pull` 补齐约 1.3 GiB 内容，不拉取额外历史；对照指针中的大小及 SHA-256 验证，不能将指针重命名或跳过 APEX 校验。构建入口新增 `check_source_lfs.py`，遇到 `vendor/pixel` 内未实体化的指针立即停止。

若 `git lfs pull` 提示未安装 LFS 而跳过 checkout，在该 GMS 仓库执行 `git lfs install --local --skip-repo`，再执行 `git lfs checkout`，仅设置该仓库过滤器，不改全局设置或已有 hooks。本次八个文件补齐后已验证大小、SHA-256、APK/APEX ZIP 校验和 gzip 内的 APK 文件头；Git HEAD 未改变、工作区干净且仍为 shallow。新增指针检查已在实际未补齐状态下拒绝构建，补齐后通过。

本次实测 `art`、`build/make`、`bionic`、`vendor/lineage` 和 Linux Clang 仓库均为 shallow，当前 HEAD 的可见历史各为一个提交。Git 对象过滤仍需下载实际检出的源码和工具链，不表示 Android 源码能够缩小到几 GB。此前逐轮试刷产生的镜像及解包副本也不受 `repo` 的最小拉取选项管理，需单独核算磁盘占用。

复用旧源码文件作为下载种子时，还须检查新清单外的旧项目以及新项目中的未跟踪旧文件，避免 Android 16 的模块进入 Android 17 构建图。本次将 17 个过期种子目录移出源码扫描范围；其中 `hardware/qcom/audio` 在原 Android 16 树中存在，但不属于当前 Android 17 清单。直接从空目录同步不会产生这些种子遗留。保留当前清单的 `copyfile`、`linkfile` 和构建系统生成的合法链接，不按目录名称猜测归属。

## 设备适配

`AndroidProducts.mk` 和 `build-pixelos.sh` 从目标树读取 release，支持本次由 `bp4a` 变为 `cp2a`，不把旧 release 硬套到 Android 17。

设备标识片段在两个产品入口中以 `include` 最终赋值。不能把它作为最后一个 `inherit-product` 父产品：Android 对单值产品变量使用父产品优先级，先继承的 `full_base` 会保留 `PRODUCT_DEVICE=generic`，使构建错误选择通用 ARM 板。已通过 Android 17 实际 `soong_ui --dumpvars-mode` 分别验证 PixelOS 和 Lineage 产品均解析为 `m2381 / arm64 / arm`，板级目录为 `device/meizu/m2381`；编译入口会再次检查设备名和主架构。

`patches/platform-17-series.json` 是独立的 Android 17 平台补丁组，包含旧 vendor libbase ABI、VNDK33 LLNDK 列表、预编译内核头生成方式和主机 Go 内存参数透传。工具根据 PixelOS major version 自动选择 Android 16 或 17 补丁组；对未知源码摘要保持拒绝应用。旧 TurboAdapter R8 绕过不自动带入 Android 17。

补丁组现为六项。原先的第七至十项（CAF display 命名空间两处、`BoardConfigQcom.mk` 机型特判、build-manifest 生成规则）已撤销，改由 `local_manifests/01-m2381-excluded-projects.xml` 的 `remove-project` 承担，详见 [补丁说明](patches.md)。

六项 Android 17 补丁已针对所取上游文件在隔离目录及同步后的实际源码中应用并核对最终 SHA-256，重复执行检查通过，未知摘要被拒绝。5418 项固定构建输入检查通过，77 项文件复制规则没有冲突，2924 项库/模块安装路径检查无错误。新编译的 32/64 位 vendor libbase 已对 123 个原厂 ELF 检查，未发现缺失符号。这些检查尚不能代替完整编译和真机验证。

完整编译首次在约 32% 处遇到内核头文件生成失败：历史 `lineage_generator` 命令直接读取设备目录，没有声明沙箱输入，而且只声明了占位输出。Android 17 的沙箱内无法读取该头文件。第五项补丁现改为标准 `genrule`，通过内核目录的 `filegroup` 显式声明输入和 `linux/msm_audio.h` 输出，确保头文件进入沙箱并被导出；没有关闭构建沙箱。该头仍是已有的编译兼容定义，不代表已获得原厂内核 UAPI，也不改变实际使用的原厂音频 HAL。

修正后已执行实际 `m generated_kernel_includes -j16`，Soong、Make 和头文件生成均通过；检查生成文件与输入字节完全相同，并确认沙箱清单包含输入复制和输出回收。完整构建继续进行，尚未刷入手机。

续编译又发现 CAF `libdrmutils` 被相同的安装路径拉入，继而需要未提供的 `display/drm/msm_drm_pp.h`。设备配置虽未主动选择源码 composer/gralloc，导出的源码命名空间仍会产生与原厂 ETC 预编译模块重叠的安装规则。第七项补丁为 `hardware/qcom-caf/sm8550/display` 单独建立不导出给 Make 的 Soong 命名空间，保留其头文件和模块定义，停止生成这部分源码的产品安装规则；第八项补充已有 QMAA 子命名空间的导入，第九项仅对 M2381 修正电源服务使用的 `libdisplayconfig.qti` 命名空间，维持全局模块解析。原厂 composer、mapper、显示库继续由厂商打包表提供，不用其他机型或占位 DRM 头文件替代。电源服务原有的源码 displayconfig 链接依赖仍保留，不在此次改动中猜测原厂库的替代 ABI。

显示归属修正后，实际构建 32/64 位原厂 `libdrmutils`、composer 服务和 64 位 mapper 四个目标通过。安装后的四个文件均与随附厂商输入字节相同；生成的 Soong Make 导出表和安装表中，CAF display 源码安装条目为零。完整系统构建及真机验证仍需继续。

完整构建续至约 82% 时，上游 `repo manifest -r` 因已隔离音频项目的工作目录不存在而失败。第十项补丁仅为 M2381 改用设备树中的 `export_build_manifest.py`：先导出当前合并清单，再读取 `.repo/projects/<path>.git` 的实际 HEAD 固定每个项目，保留上游私有项目排除规则。不会恢复 HAL 目录或使用过期静态清单；任一 Git 项目无法解析时停止，采用临时文件替换以保留已有输出。清单记录提交，平台补丁仍由本仓库补丁组独立复现。

已执行实际 `m build-manifest.xml -j16` 并通过，对导出的 1226 个公开项目逐一核对当前 Git HEAD，项目集合与同步锁定清单的相同排除结果一致。隔离的五个 HAL 目录未恢复；额外模拟缺失 Git 项目时，工具失败且保留原有输出。完整构建继续，尚未执行 Android 17 真机升级。

主机只有约 47 GiB 内存时，本次 Soong 分析曾占满内存并大量使用 swap。第六项补丁仅把显式指定的 `GOMEMLIMIT`、`GOGC` 传给原本使用 `env -i` 的解析进程，不改变目标产品配置；未设置这两个变量时保持上游默认行为。当前重试使用 `SOONG_INCREMENTAL_ANALYSIS=false GOMEMLIMIT=32GiB GOGC=30`，已在实际解析进程环境中确认生效。Go 的内存限制是软限制，仍需观察完整构建峰值。

打包阶段的 `check-selinux-treble-labeling` 曾读取原厂 ODM 整包策略，报缺少 Android 17 的 `treble_labeling_violators` 属性。已按 SHA-256 确认安装结果来自原厂旧二进制，而非当前源码生成结果。移除旧整包策略和三个摘要的导入规则，原厂文件保留不变；`configure_precompiled_policy.py` 与 `blob_exclude.txt` 防止重新提取时恢复这些规则。

本机实际安装的是 API 33 原厂 vendor CIL、平台公共符号与厂商上下文，加上震动适配策略，不能直接改装通用源码 vendor 策略。设备模块 `m2381_precompiled_sepolicy` 通过随设备目录分发的 `tools/compile_split_policy.py`，从实际安装的 Android 17 平台、33.0 映射、厂商与 ODM CIL 生成组合策略，覆盖通用预编译模块；平台摘要仍由当前源码生成。Make 显式依赖这条输入链和 secilc；辅助工具只在成功时原子替换二进制。外部 `tools/check_split_policy.py` 调用同一实现，避免离线检查与构建算法分叉。

已使用实际安装的 Android 17 分离策略完成与 init 一致的编译，并用合并结果执行上游 Treble 标签检查，通过且未关闭该检查。此编译沿用 init 的 `-N` 行为；额外去掉 `-N` 的严格检查确实发现旧厂商权限与新平台 neverallow 冲突，不能宣称 enforcing 或安全策略移植已经完成。当前设备原有 permissive 诊断配置仍在，平台源码的 `sepolicy_neverallows` 构建要求保留。完整构建目标的验证结果与真机启动仍需另行核对。

实际执行 `m check-selinux-treble-labeling -j16` 成功，确认检查时间戳为空且非“跳过检查”结果。安装的组合策略 SHA-256 为 `d317ee589232a36fc41b3c171968de5214dfac05e796ca0f3f703d820e3bfd4d`，与离线复编译结果一致，区别于原厂二进制的 `fa056d00e5b3c89f8162233b6f15f66d7168d181e92a70702e152d34deb6e0bf`。额外验证了重复编译字节一致、失败时保留既有输出并清理临时文件；2924 项库安装路径检查仍无错误。

完成源码同步后需依次验证：产品解析、依赖/Soong 配置、VINTF/FCM、32/64 位 vendor ABI、完整构建，以及匹配诊断启动链的候选测试。保留 OpenGL 原生修复、Wi-Fi/蓝牙接入、震动幅度和屏幕/相机覆盖，不重新引入已撤回的图形绕过。

## 首次完整构建与离线验证

本次 `m pixelos -j16` 已成功，输出 `PixelOS_m2381-17.0-20261115-0353.zip`，实际系统属性为 Android 17、SDK 37、安全补丁 2026-11-01。设备身份文件仍显式使用历史 donor fingerprint，因此 OTA 的 `post-build` 字符串仍含 Android 16；判断实际平台版本须同时核对系统属性和 OTA 的 `post-sdk-level=37`，不能仅凭 fingerprint 推断。

已验证 OTA ZIP CRC、payload 全部字节的 SHA-256 与长度、metadata SHA-256，均与 payload properties 一致。七个 EROFS 分区全部实际提取并通过文件系统检查；32/64 位 runtime 与 VNDK33 APEX 内容、工具链接、BoringSSL 自检程序架构、123 个厂商 ELF 的 libbase 符号、304 个 vendor_dlkm 模块和实际镜像分离策略编译均通过。构建的 `check_vintf_compatible.log` 和 OTA 打包的 VINTF 检查均返回 `COMPATIBLE`；原始镜像的完整 AVB 描述符和哈希树链验证通过。

另已离线准备第 48 组诊断候选：使用当前全部分区镜像与新 init_boot，保留第 47 组 vendor ramdisk 全部条目和 DT，只有 first_stage 日志组号及 bootconfig 的诊断 rc 路径改变。第二阶段 staged init 来自实际提取的 Android 17 镜像，未复用 Android 16 init。诊断 rc 通过 Android 17 host_init_verifier；预编译组合策略与提取镜像重新编译结果相同。顶层与子链分别用预期密钥验证，子链回滚位置为 2，并执行完整链哈希检查。这些是离线证据，尚不能代替启动和硬件验证；默认 OTA 本身也不会安装所需 metadata 脚本。

## 第 48 组真机升级

升级前已备份 8 GiB super、B 槽启动/AVB/dtbo/recovery、misc 和 metadata 诊断目录，各分区与设备端 SHA-256 核对一致。保留第 47 组候选、原厂输入和已有 Windows 备份。沿用已验证的原厂 recovery/fastbootd 路径更新七个 B 槽逻辑分区，诊断 recovery 中确认 userdata 未挂载；通过 super 元数据的物理区段完整回读七个分区，大小与摘要全部匹配，slot 0/1 元数据一致。然后安装候选 boot/init_boot/vendor_boot/vbmeta_system/vbmeta 和第 48 组 metadata，未清除数据。

首次约 34 秒完成启动，zygote、SurfaceFlinger、system_server 持续运行，超时服务自动停止。用户确认桌面画面和触摸正常；一次正常重启后 boot ID 变化、Android 17/SDK 37 与 B 槽身份保持，Wi-Fi 自动重连并通过联网验证。启动/AVB 五个分区在系统内再次回读 SHA-256 均与候选匹配；第 47 组入口文件摘要未变。

ARM 与 ARM64 的 OpenGL ES 2.0/3.0/3.1/3.2 像素绘制各 4/4 通过，未恢复强制 Vulkan 绕过。Chrome 启动并持续存活，颜色页正常启动，主摄预览建立；蓝牙 ON、管理器无崩溃。完整蓝牙传输/音频、全部镜头 JPEG、震动手感、移动网络、GNSS、指纹、音频和 NFC 未全部执行本版验收，详见 [功能状态](status.md)。原有 permissive 与诊断依赖仍在，不作为可直接发布的通用 OTA。

## 充电服务后续更新

源码设备 Health 适配和 SystemUI 快充阈值见 [充电适配](charging.md)。重新生成 vendor 规则后运行 `python3 tools/configure_health.py /path/to/android`，保留原厂输入，仅排除被源码服务替代的三项安装规则。

重启后电脑 PD 零输入的后续驱动兼容修正、固定摘要和四次连接重启验证见 [充电适配](charging.md)。同步设备/vendor 目录时应包含独立 `compat` 副本；构建前执行 `python3 tools/configure_pd_icl.py --root /path/to/android` 核验，缺失时审阅后用 `--apply` 复现。原厂输入保留不变，未知版本拒绝自动套用。
