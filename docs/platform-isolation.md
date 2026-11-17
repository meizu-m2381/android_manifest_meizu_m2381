# Android 17 设备适配与平台隔离

当前迁移将 M2381 的兼容处理留在设备/vendor 仓库，不再要求六项 Android 17 平台补丁。历史补丁保留用于识别和撤销已有工作区；不能再用 `--apply` 重新应用 Android 17 补丁。

## 上游依据

先对照 LineageOS 官方提交及 WSL 当前源码，采用已有接口：

| 问题 | 官方实现 | 本设备的接入 |
| --- | --- | --- |
| 旧 `Trim` 签名 | [421619](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/421619) | 使用现有 `libbase_shim` |
| 旧 `Basename` / `Dirname` 签名 | [465067](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465067) | 使用同一官方 shim |
| 旧 `WriteStringToFd` 签名 | [465271](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/465271) | 使用同一官方 shim |
| SM8550 blob 接入 shim | [472159](https://review.lineageos.org/c/LineageOS/android_device_xiaomi_sm8550-common/+/472159)、[官方提取配置](https://github.com/LineageOS/android_device_xiaomi_sm8550-common/blob/lineage-23.2/extract-files.py) | `patchelf --add-needed libbase_shim.so` |
| 另一种旧 ABI 方案 | [465028](https://review.lineageos.org/c/LineageOS/android_device_oneplus_sm8550-common/+/465028) | 上游使用 `replace_needed` 改为 `libbase-v33.so`；本设备不需要替换整份 libbase |
| 预编译内核头接口 | [427578](https://review.lineageos.org/c/LineageOS/android_vendor_lineage/+/427578)、[490401](https://review.lineageos.org/c/LineageOS/android_build_soong/+/490401) | `TARGET_PREBUILT_KERNEL_HEADERS`，保留通用生成器 |

二进制 patch 在这里修改 ELF 的依赖表，让动态链接器加载真实兼容实现。旧 `std::string` 引用和新 `std::string_view` 参数的调用约定不同，不能只把符号字符串改名当成 ABI 适配；也不使用空函数冒充实现。

## 设备专属输入和配置

`device/meizu/m2381/configs/compat/libbase-fixups.json` 固定 14 个实际打包的原厂 ELF 的原始摘要、修补摘要和旧符号。`tools/configure_blob_compat.py` 使用随源码提供的 `patchelf-0_17_2` 生成 `vendor/meizu/m2381/compat/vendor/...`，只切换对应安装规则。原始 `proprietary/` 不改写。工具先检查全组输入和已有输出；未知输入、输出冲突或规则重叠均停止。已记录摘要的旧兼容副本可以用 `--apply` 升级，检查模式拒绝未升级副本。32/64 位官方 libbase shim 和 32 位官方 vendor libui shim 由设备产品显式选择。

原 VNDK33 LLNDK 清单补丁源于源码构建的 **vendor libbinder** 依赖当前系统 `libapexsupport.so`。当前 VNDK33 快照中的 libbinder 不含该依赖。设备改用 `PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS` 的 `requireLibs`，不修改冻结的 VNDK33 清单；需校验最终 linker 配置与依赖可达性。

`PRODUCT_SOURCE_ROOT_DIRS` 的负路径只在 M2381 产品中排除 stock HAL 对应的 Soong 定义。local manifest 不再移除 CAF display、audio、STHAL、IPA 项目，其他产品可以在同一 checkout 中使用这些源码。`core-utils-vendor/fwk-detect` 同样仅在本产品中排除，以保留原厂库及 CneApp 链接。它不是对其他设备构建成功的替代验证。

恢复完整源码项目后，Make 暴露了设备自定义 RFS 软链接与 `hardware/qcom-caf/common` 的 24 处重复安装定义。现改为引用上游同路径、同目标的模块，不再重复声明。

内核仓的 `kernel-headers.tar.gz` 是有限的编译兼容输入，包含已有 `msm_audio.h` 和上游清理工具要求的三个通用头。可用 `tools/package_build_headers.py --aosp AOSP_ROOT` 复现。它不是完整的原厂 UAPI，不能据此启用源码 QTI 音频/显示 HAL。上游头依赖选择器读取 shell 环境，因此构建入口在 lunch 后从实际 BoardConfig 导出该变量。

## 从旧工作区迁移

先审阅和提交已有更改，保存可回退点；不要混入临时镜像或日志。同步三个 split 仓库与本 manifest 工具仓后：

```bash
android_root=/path/to/android
port_root=/path/to/android_manifest_meizu_m2381
cp "$port_root"/local_manifests/*.xml "$android_root/.repo/local_manifests/"
cd "$android_root"
repo sync -c -j4 --no-clone-bundle --no-tags
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --restore
python3 device/meizu/m2381/tools/configure_blob_compat.py --aosp "$android_root" --apply
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --require-unpatched
bash "$port_root/scripts/build-pixelos.sh" "$android_root" 12
```

新同步的已打包 vendor 仓库包含兼容副本，`--apply` 可重复执行。恢复器仅识别记录的 before/after 摘要；其他本地改动必须人工审阅，不能强制覆盖。它恢复文件内容，不删除历史提交。

手动构建也需使用上游头选择接口；变量只传给这次构建，避免切换其他产品后残留设备头路径：

```bash
source build/envsetup.sh
lunch custom_m2381-cp2a-userdebug
TARGET_PREBUILT_KERNEL_HEADERS="$(get_build_var TARGET_PREBUILT_KERNEL_HEADERS)" m pixelos -j12
```

主机内存补丁已退出必需项。原 `env -i` 会清除外壳的 Go 内存参数；只在外壳 export 不代表 Soong runtime 已收到。本轮有限内存验证直接给构建生成的 `soong_build` 命令传入 `GOMEMLIMIT=32GiB GOGC=30`。整条构建流水线另使用仅位于 `out` 的临时 host 启动包装，向同一原版 ELF 传参，验证后恢复两个生成工具路径；不改 AOSP 源码或原版 ELF 内容。充足内存的常规构建不需要这个操作。

本轮构建、静态 ELF、失败保护和源码恢复证据见后续验证记录；构建通过不等于已刷机或全部硬件回归通过。当前 Android 16 补丁仅作历史归档，尚未按此方案重验。

## 2026-11-16 验证结果

本轮以 WSL `/home/zhaiy/pixelos17` 的 Android 17 checkout 验证，设备、内核和 vendor 的 Windows 提交分别为 `3d62681`、`f4670f8`、`fdc958b`。WSL 对应提交为 `36aec52`、`1bf5c59`、`b60fc2e`；提交信息不同，适配文件内容一致。

| 验证 | 结果与边界 |
| --- | --- |
| 平台还原 | 六个记录文件均符合 before SHA-256；四个平台仓库恢复提交为 libbase `360ce34`、VNDK33 `e9c3e23`、Lineage `d24a238`、Soong `5c82054` |
| 迁移及失败保护 | 7 项测试通过，包括真实六项旧补丁还原、13 个真实 blob 重复修补、未知输入及输出冲突时不写入 |
| 安装规则 | 5418 个本地输入、2924 个库路径检查通过；77 条复制规则无 blob 目标冲突；生成的 Soong 安装清单没有重复目标 |
| 产品隔离 | 恢复 manifest 中原排除的 10 个项目；M2381 完整 Soong 分析与 Make 规则生成通过；`aosp_arm64` dumpvars 中设备源码过滤、设备 namespace 和预编译头变量为空 |
| 实际目标构建 | 从已生成的产品图通过 Ninja 续编，退出码 0；未跳过编译动作，但复用了已生成的产品构建图，未重新执行 lunch/Soong 分析 |
| 内核头 | 未修改的上游 `prebuilt_kernel_includes` 实际生成 `msm_audio.h`，内容与输入相同；归档可逐字节复现 |
| ELF 安装产物 | 13 个实际安装 blob 全部匹配修补后摘要；32/64 位官方 shim 均已安装；当前 vendor 中 156 个引用 libbase 的 ELF 没有缺失的 `android::base` 强引用符号 |
| 排除残留补丁 | 两种架构所需的三个旧签名在当前 libbase 中缺失，均由官方 shim 导出；因此符号检查不依赖历史 libbase 补丁 |
| VNDK33 | 重新构建并提取真实安装的 VNDK33 APEX，LLNDK 清单没有添加 `libapexsupport.so`；快照 libbinder 不依赖它，源码 vendor libbinder 依赖它 |
| linker 对照 | 从 41 个实际安装 APEX 提取 host 验证根目录，普通模式生成配置成功；设备 fragment 让 `[vendor]` 的 default、`[system]` 和 `[unrestricted]` 的 sphal 链接到系统 libapexsupport；去掉 fragment 后这些链接全部消失 |

实际构建目标包括 `libbase_shim`、`libtinycompress`、`android.hardware.boot-service.qti`、`prebuilt_kernel_headers`、host `linkerconfig`、两种架构的 vendor libbase/libbinder、13 个兼容 blob、vendor linker protobuf、`llndk.libraries.33.txt` 及 `com.android.vndk.v33`。主机的两个 Soong 工具路径已恢复为原版 ELF，七个相关 WSL Git 仓库干净。

保留在 WSL `out/` 的证据：

- `m2381-no-platform-resume.log`：成功续编日志。
- `m2381-no-platform-libbase-abi.json`：156 个引用 ELF 的符号审计。
- `m2381-no-platform-validation.json`：本轮结果及验证边界。
- `m2381-no-platform-linkerconfig/ld.config.txt` 与 `m2381-no-platform-linkerconfig-control/ld.config.txt`：有/无设备 fragment 的实际生成配置。
- `m2381-no-platform-revisions.xml`：本轮源码版本清单。

全根目录的 host `--strict` 检查仍被现有 system 配置的 `libdexfiled.so` 需求拦住；普通模式同时提示缺少 `system/etc/vndkcorevariant.libraries.txt`。上述 linker 结果只证明本设备新增依赖的配置可达性，不表示整棵暂存根目录已通过严格依赖校验。未构建全量 OTA，也未进行迁移版本的刷机、启动或硬件回归；下面另记已完成的真机进程隔离测试。

Make 仍有历史 blob 对源码安装规则的覆盖警告，包括 libtinycompress；本轮修复的是恢复公共项目后出现的重复软链接，不能把它等同于全部历史安装归属已清理。

## 2026-11-16 真机进程隔离测试

**本节是修复前的历史结果；后续修复见下一节。** 当时测试发现一个新方案的跨命名空间问题，不能以先前 156 个 ELF 的符号集合审计作为运行时兼容保证。

手机运行的是带旧 libbase 补丁的 Android 17，root adbd、SELinux permissive。测试没有刷分区或重启，也没有启动第二份传感器/NFC/指纹服务。原生启动器先调用 `unshare(CLONE_NEWNS)`，再调用 `mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL)` 并检查错误，随后只在子进程挂载视图中叠加以下输入：本次无补丁 vendor libbase、32/64 位官方 shim、13 个兼容 blob、原始 VNDK33 LLNDK 清单和现场生成的 linker 配置。其余依赖仍来自手机现有系统，因此这不是完整新镜像的启动验证。

| 检查 | 结果与解释 |
| --- | --- |
| 旧 ABI 行为 | 32/64 位各 12 项通过：Trim 三种输入、Basename、Dirname、WriteStringToFd 成功/内嵌 NUL/无效 fd，以及四个旧签名的实际提供者检查；提供者均为 vendor libbase_shim |
| 依赖发现 | 13/13 的 `linker --list` 通过；该模式不执行符号重定位，不能单独证明程序可启动 |
| 11 个共享库的真实加载 | 最小 DT_NEEDED 可执行程序完成重定位和库构造，修补版 10/11 退出 0；未调用 HAL 业务接口 |
| 原始 blob 对照 | 同样使用无补丁 libbase，原始版只有两个 boot_control 库通过；其余 9 个失败。32 位 codec2 首先遇到另一处缺符号，不能将全部失败都归为 libbase |
| 传感器服务依赖探针 | 按真实服务 DT_NEEDED 顺序链接、显式引用旧 WriteStringToFd 的最小程序：原始依赖失败，增加 shim 后退出 0；没有执行真实 daemon 的 main |
| qguard 依赖探针 | 保持真实 DT_NEEDED 顺序后，增加 shim 仍失败：VNDK33 libprocessgroup 缺旧 WriteStringToFd。手机原有带补丁 libbase 的同类基线探针退出 0，故这是移除补丁后暴露的阻塞 |
| 现有系统基线 | 不更换任何系统库时，11 个共享库仍是 10/11 通过；32 位 codec2 同样失败，证明该项不是本次添加 shim 引入 |

两个剩余问题：

- `vendor/lib/libcodec2_hidl@1.0.so` 缺 `_ZNK7android19GraphicBufferSource25getHGraphicBufferProducerEv`。原有系统、原始 blob 加无补丁 libbase、修补版三组均失败。这是现有 32 位媒体依赖问题，尚未修复。
- qguard 依赖的 `/apex/com.android.vndk.v33/lib64/libprocessgroup.so` 缺旧 `WriteStringToFd(const std::string&, borrowed_fd)`。实际 VNDK33 libprocessgroup 与本次构建提取产物摘要一致；APEX 自带 libbase 虽然导出旧签名，现场依赖选择/符号作用域仍未使该引用可用。在 vendor 可执行文件上添加 shim 并未覆盖这条跨命名空间依赖，需继续定位并采用设备局部方案，不能回写公共 libbase 或直接放宽全部 namespace。

隔离工具预检曾短暂产生传播到系统视图的空挂载，已立即卸载；之后改为上述直接系统调用的启动器，并检查 PID 1 mountinfo 无测试挂载残留。早期两个临时诊断 ELF 因多次 patchelf 改写导致自身重定位崩溃，其结果已排除；最终依赖探针在链接时生成准确的依赖顺序，不再反复改写 ELF。这些诊断崩溃不能记为产品 blob 崩溃。

测试前后 boot ID、原系统 32/64 位 libbase 摘要相同，boot_completed 仍为 1；原传感器、NFC、健康和指纹服务 PID 未变。原有 `vendor.dpmd` 的 Parcel::setData 缺符号日志也不属于本轮引入。以上服务存活只证明原系统仍运行，不代表迁移后的硬件通过回归。

原始日志、最终探针、编译命令及挂载快照仅保存在机主本地 `.local-flash/platform-isolation-20261116/`，不随仓库发布。`results-*/` 状态文件保留多轮追加记录，应取每项最后一次结果，不能累计早期无效探针。旧 ABI 行为检查源码保存在 `tools/libbase_behavior_probe.cpp`，需要用匹配 Android 源码的 bionic/libc++ 和真实 vendor shim 构建成两种架构的 vendor 可执行程序；不可将桌面 C++ 测试替代真机结果。

## 2026-11-17 修复真机加载阻塞

qguard 改由本产品选择上游现有 `libprocessgroup.vendor:64`，安装当前源码构建的 vendor 库。原来没有该 vendor 库时，依赖落入 VNDK33 namespace，旧 libprocessgroup 又共享到了当前 vendor libbase。直接给 qguard 增加 shim 无法为这个 namespace 内的旧引用提供符号；选择当前 vendor 实现后，不再经过这条旧依赖。未修改 libprocessgroup、libbase、VNDK 或 linker 的公共源码。

32 位媒体栈保留原厂 codec2，同时做两项设备侧修补：

- 将原厂 `libcodec2_hidl@1.0.so` 的 helper 依赖改为单独命名的 `libstagefright_bufferqueue_helper-v33.so`。设备 Make 模块从冻结 VNDK33 的 32 位输入生成这个副本，只改 SONAME 并增加 libbase_shim；输入与输出摘要均由 `media-helper.json` 固定。当前 OMX 仍可使用当前 helper，冻结的 APEX 输入不变。
- 给原厂 `libcodec2_vndk.so` 增加官方 `libui_shim.so`，补齐旧 GraphicBufferMapper::lock/lockAsync/unlock 调用。采用 LineageOS 已合并的 [394610](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/394610) 和 [394611](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/394611)，不是把 HIDL 2.0 getter 重命名为 HIDL 1.0，也没有自写空实现。保留 VNDK 库并改 SONAME 的做法可参照官方 [410069](https://review.lineageos.org/c/LineageOS/android_hardware_lineage_compat/+/410069)。

无补丁 libbase 的同一真机隔离环境中，原 11 个共享库加新增的 codec2_vndk 独立探针共 **12/12** 完成重定位/构造；**14/14** 的依赖发现通过。撤去这两项媒体修补及 vendor libprocessgroup 后，codec2 的 getter 缺符号、codec2_vndk 的 mapper 缺符号和 qguard 的旧 WriteStringToFd 缺符号再次出现，形成失败对照。

`tools/build_vendor_relocation_probe.py` 在链接时保持原服务的 DT_NEEDED 顺序，为全部强引用符号名生成实际重定位。传感器服务 197 个、qguard 142 个强引用名检查均退出 0；该工具不检查原符号版本、弱引用、dlopen 路径或原程序 main，不能替代真实服务和硬件回归。

`tools/media_helper_behavior_probe.cpp` 使用冻结 API33 头文件构建，验证准确对象布局下的 GraphicBufferSource 构造/析构、initCheck、HIDL 1.0 和 2.0 producer getter，并检查旧 getter 来自独立 helper，真机退出 0。两种架构各 12 项 libbase 行为检查也继续通过。上述检查没有执行视频编码、相机采集或实际 gralloc 映射，媒体功能仍需完整刷机后验证。

迁移及失败保护测试扩展为 9 项，全部通过，包括已知旧兼容副本升级、未知输入保护，以及 helper 可复现且不改写上游输入。重新执行了 Soong 分析和 Make 规则生成；设备 Makefile 同步时统一为 Linux 换行，修复 CRLF 输入造成的原策略命令 Ninja 解析错误。分析进程使用仅在生成工具启动时注入的 Go 内存参数，两处生成工具在结束后恢复为原版 ELF。

五个实际安装目标经 Ninja 构建退出 0：vendor 64 位 libprocessgroup、32 位 libui_shim、单独命名的 VNDK33 helper，以及两个修补后的 32 位 codec2 库。14 个安装 blob 全部符合固定修补摘要，helper 符合其固定摘要。最终真机测试使用了镜像暂存目录中这批实际安装产物，结果与候选输入测试一致。2924 个库安装路径审计无错误；当前 vendor 的 158 个 libbase 引用 ELF 无缺失 android::base 强符号；六项公共源码 before 摘要继续通过。符号集合审计仍不能替代 namespace 下的真实加载。

构建和真机最终产物验证记录在机主本地 `out/m2381-runtime-fix-targets.log`、`out/m2381-runtime-fix-installed-abi.json` 与 `.local-flash/platform-isolation-20261116/final-results/`、`final-control/`、`installed-inputs-sha256.json`，不提交设备标识或原始日志。手机 boot ID、系统 libbase 摘要及原服务 PID 未变，PID 1 无测试挂载残留；本轮仍未刷机、重启或进行完整硬件回归。


## 2026-11-17 完整启动测试与动态加载回归

用户选择完整启动和硬件测试后，先备份当前 B 槽启动/AVB/recovery/dtbo/misc、完整 8 GiB super 和 metadata 诊断目录。按当前生成的产品文件清单，使用已有安装产物重新打包七个 EROFS 镜像；没有把历史 OTA 当作新版本。整包目标的缓存失效触发大量重编，已主动中止，因此这次是安装目录重打包及定向刷入验证，不是全量源码构建或通用 OTA 验证。

七个逻辑分区在官方 fastbootd 写入后，按更新后的 super extent 回读摘要全部匹配；两份 super metadata 布局一致。保留已验证的 boot/init_boot/vendor_boot、诊断 recovery 和 metadata 配置，重签配套 AVB 后启动。首次新启动完成，21 个关键 vendor 文件、两份无旧符号的 system libbase 和五个启动/AVB 分区摘要核对通过。用户数据未擦除。

完整启动暴露了先前探针没有覆盖的 dlopen 路径：相机和音频主 HAL 通过 libutilscallstack 进入 VNDK33 libbacktrace，旧 Basename 引用无法由当前 libbase 解析。相机 provider 因加载失败后的空指针反复崩溃，AudioPolicyManager 也没有正常初始化。此前依赖探针、符号集合审计和 21 个文件摘要全部通过，仍不足以证明这些动态加载路径正常。

当前源码已构建的 vendor libutilscallstack/libunwindstack 当时仅存在于暂存目录，没有进入产品文件清单。设备现显式选择上游 `libutilscallstack.vendor` 与 `libunwindstack.vendor` 的两种架构，保留公共源码和冻结 VNDK33 输入。独立挂载命名空间补齐这两份现有 vendor 库后，camera.qcom、audio.primary.kalama、sound_trigger.primary.kalama 和三份高通音效库均完成 dlopen/重定位/构造。仅补 libutilscallstack 时仍落入旧 libunwindstack，失败对照表明两层依赖均须打包。

首次启动后曾发生 `reboot,rollback_staged_install`。dumpsys rollback 记录本机已有 vendor.dpmd 连续 native crash 触发已暂存 ExtServices 模块回滚；这是实际重启事件，不能忽略，也不能据后续进入桌面判定长期稳定性通过。原有 dpmd 的 Parcel::setData 缺符号仍待解决。

原始分区、照片、标识、网络信息和日志仅保留在机主本地 `.local-flash/platform-boot-20261117/`，不提交仓库。


### 回溯依赖修复版刷入结果

Make 在主机 PATH 工具中遇到 Go `newosproc` 线程创建失败；同一配置直接执行 ckati 成功。随后只使用新生成的 vendor 文件清单与镜像规则重打包，四份新增的 32/64 位 libutilscallstack/libunwindstack 全部进入产品清单，镜像提取摘要与安装输入一致。主机两处 Soong 生成工具恢复为原版 ELF，六项公共源码摘要符合记录的上游输入。

修复版只更新 vendor 与配套父 vbmeta，其他十份候选镜像保持首轮字节。AVB 父签名、子链及各分区哈希树校验通过；vendor 刷入后按 super extent 回读一致。B 槽启动完成，25 个实际安装输入、五个启动/AVB 分区、两份 system libbase 和 metadata 诊断配置核对通过，用户数据保留。

相机恢复枚举 5 个 HAL 设备，普通应用可见主摄与前摄两个设备；音频策略管理器恢复初始化。新启动已复测：32/64 位 GLES 各 4/4；两种架构分别调用 C2 与 OMX 高通 AVC 编码器，每项 10 帧并收到 EOS；加速度、陀螺仪、光线、接近四类传感器均注册并收到事件。接近传感器是 on-change 缓存事件，不能记成连续新采样。

短时静态屏幕录制生成 1080×2400 AVC 文件，使用真实 `c2.qti.avc.decoder` 解出一帧并收到 EOS，仅证明该静态画面的 surface 编码/硬件解码链路，不代表多帧相机录像通过。NFC 开启、指纹 HAL 暂无死亡记录均只是服务状态证据。

修复版启动后仍观测到原有 `vendor.dpmd` 的 Parcel::setData 与 `slim_daemon` 的 __emutls_get_address 缺符号；未把它们当成本次相机回溯依赖修复已解决的问题。dpmd 可继续参照官方 [libhidlbase shim 扩展](https://github.com/LineageOS/android_hardware_lineage_compat/commit/6abd82960c3865dfd70b6ae10aead696271e91db) 单独验证。蓝牙音频的可选实现加载错误也仍待查，通话、移动数据、蓝牙耳机、触摸指纹认证、快充和长期待机未完成验证，SELinux 仍为 Permissive。

重启后真实拍照与录放测试需要用户再次解锁，结果另行补充。真实相机 provider 已占用硬件时，再用独立 dlopen 探针加载 camera.qcom 会在 CamX 构造时因资源状态 abort；这是额外探针引入的诊断崩溃，不算 provider 自发崩溃，也不作为镜像加载成功证据。主机录像探针曾因推送旧 dex 找不到入口而中止，更新 dex 后成功；早期无效探针结果不计入通过数量。


诊断时两次用管道提前截断 `dumpsys media.camera` 输出，与两次 provider 的 SIGPIPE 退出时间对应；后续改为完整保存 dump。SIGPIPE 重启必须记入诊断影响，不能宣称 provider PID 始终不变，也不能与最初缺符号的反复 SIGSEGV 混为一谈。音频服务 PID 与启动后记录相同；后续相机实际采集仍须另外验证。


解锁后的真机拍摄与音频采样已完成。Camera2 分别打开主摄、超广角、前摄，生成 4080×3060、4640×3480、3840×2160 JPEG；三张文件均完整解码。加入 640×480 预览并等待 AE 收敛后再拍，三个设备均报告 AE_CONVERGED。前摄照片有清楚室内细节。主摄和超广角样片拍到非常近的棕色平面，像素变化接近均匀，不能凭文件可解码就宣称其成像质量通过；需要无遮挡且有细节的正常场景再验焦点和图像。

麦克风使用 AudioRecord 采到 96,000 个 PCM 样本，RMS 非零。AudioTrack 向系统 MEIZU 20 路由写入并播放了 48,000 帧 440Hz 测试音；硬件报告 playback head 到达末尾，但没有取得人的听觉确认，所以只证明播放数据路径。1280×720 主摄录像持续约 3.4 秒，MP4 含 93 个 AVC 视频样本和 159 个 AAC 音频样本；`c2.qti.avc.decoder` 成功解码 93 帧并收到 EOS。没有把容器含音轨误报成音频可听。

用户尚未报告扬声器实听，也未确认调整后置镜头朝向正常场景。所有测试位于 boot ID `9ed2044b-1a57-40c5-984f-446d3fef0346`；测试后主相机 provider、audioserver、vendor audio service 仍使用原 PID，完整保存的相机服务 dump 未截断，检查没有测试挂载留在 PID 1。Wi-Fi 连接且 VALIDATED，电池显示 AC powered；未验证通话/移动数据、蓝牙耳机、指纹触摸认证、快充电流行为、休眠待机。相机测试应用和原始/缩略图像仅在本地 `.local-flash/platform-boot-20261117/camera-fix/`，不提交仓库。


后续在用户摆正手机、露出镜头并朝向有细节的明亮场景后复拍：主摄 4080×3060、超广角 4640×3480、前摄 3840×2160 三张 JPEG 均完整解码，三者预览 AE 均收敛。两张后摄样片可辨认桌面物品与包装文字等场景细节，后置成像质量的此前疑点解除。该复拍没有触发重启，仍是同一个 boot ID。用户没有注意到先前测试音，因此扬声器的实际听感仍未确认。


## 2026-11-17 Aperture 60 帧录像设备配置

当前 HAL 在标准 `CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES` 中只公布至 30 fps，但魅族私有视频能力表含 60 fps。Aperture 从 CameraX 标准帧率集合生成界面，因此默认只显示到 30。采用上游已有 `config_additionalVideoConfigurations` 数组，在本设备 overlay 中为 ID 0/1/3 的 hd/fhd/uhd 增加 60，不修改公共 AOSP、Aperture、CameraX 或冻结 VNDK 源码；深度相机 2、逻辑相机 4 继续隐藏，未添加 120/240 fps。

使用 Camera2 普通录像会话、MediaRecorder 与真实麦克风，对三摄×720p/1080p/4K 九组明确请求 `[60,60]`，每组录制约 4 秒。逐帧检查传感器时间戳和 MP4 视频样本时间戳，避免只验证容器帧率标签。全部输出有效视频：720p/1080p 约 59–60 fps，4K 约 58 fps；传感器中位间隔约 16.66–16.67 ms。4K 在本次短测中有少量丢帧，不能称持续恒定 60 fps，也未做热稳定长录像。

真实 `ApertureOverlayM2381` 目标构建退出 0；只更新设备资源输入，依赖的 host 工具和 framework-res 由标准图重建。打包时发现旧的独立 product 镜像规则未跟踪暂存 APK 变化，已强制重建，随后从最终 EROFS 提取 overlay，确认 SHA256 与新安装产物相同。AVB 子签名和完整父子链验证通过。静态 overlay 不能 adb install 更新，临时动态 overlay 方案被自动审批拒绝，因此最终使用产品镜像刷入验证，未用临时覆盖冒充持久生效。

保留原备份和既有 vendor 修复，只定向刷 B 槽 product，并更新 vbmeta_system，父 vbmeta 因子链公钥未变而字节相同。按 super extent 回读 product 匹配；未擦除用户数据，metadata 诊断配置保持原摘要。启动完成后核对 25 个关键输入、五个启动/AVB 分区、两种架构 system libbase 和新 overlay 均匹配。`cmd overlay lookup` 确认 Aperture 实际解析到三组 `hd|fhd|uhd/60`；应用界面和应用实际录像待用户本次重启解锁后继续，不能用 Camera2 探针通过代替 Aperture 实录。

九组实录、传感器时间戳、视频样本统计、构建产物、原 overlay 备份与刷入回读证据仅保存在本地 `.local-flash/platform-boot-20261117/fps-fix/`。旧 `dpmd` 和 `slim_daemon` 缺符号未在这项配置修复中处理。
