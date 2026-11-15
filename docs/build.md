# Meizu 20 Android 16 构建准备

`pixelos-17` 分支的 Android 17 同步和适配方法见 [升级说明](upgrade-pixelos17.md)。本页保留 Android 16 构建参考；不要将下面的 sixteen-qpr2 同步命令用于本次 17 升级。

本归档针对 PixelOS `sixteen-qpr2` / 16.2、LineageOS 23.2、`bp4a`，不是 Android 17。已有完整构建曾成功，但本次整理后的仓库未做全新同步后的全量编译或刷机测试；平台补丁会拒绝未知源码摘要，遇到拒绝必须审阅差异，不能强行套到新分支。

## 1. 源码环境

在 Linux/WSL 准备足够空间、内存和 PixelOS 官方构建依赖，包括 repo、Git LFS、Python 3.11+、Git、rsync，以及匹配分支的工具链。以官方构建说明为准。初始化独立 Android 源码目录：

```bash
mkdir -p /path/to/android
cd /path/to/android
repo init -u https://github.com/PixelOS-AOSP/android_manifest.git -b sixteen-qpr2
# 本归档参考 manifest 的固定版本；这并不会固定所有项目的分支尖端。
git -C .repo/manifests checkout e37ff60b6e27a3c51f3c6ab01a42473bec7aa2a2
repo sync -c -j4
repo manifest -r -o local-revisions.xml
```

manifest 参考副本在 `provenance/pixelos-manifest`。它包含分支引用，**不是全树 revision lock**。旧 WSL 工作区没有完整 `.repo`，无法恢复当时所有子仓库提交。本归档记录已观察到的平台文件 before/after 摘要；新同步树如果已变化，需要重新移植补丁。不要为节省空间删除 `.repo`，也不要用历史占位 manifest 替代真实版本信息。GMS 的 LFS 对象应实际下载，不能把 LFS 指针文件打包当 APK。

## 2. 原厂输入和设备目录

先在本仓库执行 `git lfs pull`，再按 [输入说明](local-inputs.md) 核验随附依赖，无需先从自己的手机提取。设置本次 shell 使用的路径：

```bash
port_root=/path/to/m2381
android_root=/path/to/android
python3 "$port_root/tools/check_bundled_inputs.py"
python3 "$port_root/tools/check_local_inputs.py"
mkdir -p "$android_root/device/meizu" "$android_root/vendor/meizu"
rsync -a "$port_root/device/meizu/m2381/" "$android_root/device/meizu/m2381/"
rsync -a "$port_root/device/meizu/m2381-kernel/" "$android_root/device/meizu/m2381-kernel/"
rsync -a "$port_root/vendor/meizu/m2381/" "$android_root/vendor/meizu/m2381/"
```

对已有 Android 工作区先审阅/提交本地更改并备份同名目录。以上同步会更新同名文件，不使用 `--delete`。不要同时在这些目录叠加其他设备树或旧生成规则。

## 3. 平台适配

本适配不编译的 QTI 源码栈（CAF display、CAF audio、开源 STHAL、IPA）由 `local_manifests/01-m2381-excluded-projects.xml` 里的 `remove-project` 移除，不用改名目录：

```bash
cp "$port_root"/local_manifests/*.xml "$android_root/.repo/local_manifests/"
repo sync -c -j4 --no-clone-bundle --no-tags
```

先确认移除生效，再检查、应用已记录补丁：

```bash
repo manifest | grep -c "qcom-caf/sm8550/display"   # 期望 0
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root"
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --apply
```

`remove-project` 是 `repo` 的正式机制：项目和它的工作目录一起消失，`repo manifest -r` 不会再遇到「清单里有、磁盘上没有」的项目。旧做法是在构建前把源码目录改名到 `out/m2381-disabled-sources`，目录仍在 manifest 里，打包阶段生成清单时必然失败；该做法及其工具已移除。

`hardware/qcom-caf/common/nqnfcinfo` 不是独立项目，而是 `LineageOS/android_hardware_qcom-caf_common` 的子目录，无法用 `remove-project` 移除。它的 `nqnfcinfo` 模块不在 `PRODUCT_PACKAGES` 里，从不进入构建图；设备使用 `mz_vendor_bin_nqnfcinfo` blob，安装路径不冲突。

`USE_DEVICE_SPECIFIC_DATA_IPA_CFG_MGR := true` 在设备 `BoardConfig.mk` 中设置，阻止 `BoardConfigQcom.mk` 把已移除的 `data-ipa-cfg-mgr` 路径加进 `PRODUCT_SOONG_NAMESPACES`。

TurboAdapter 的历史 R8 规避补丁默认为可选；只有重现相同编译问题时，审阅后给平台工具加 `--include-r8-workaround`。`msm_audio.h` 是历史编译占位头，不可用于验证真实内核 ABI。更换成源码音频栈需要真实匹配的 UAPI。

vendor makefile 已包含当前 Wi-Fi/Adreno 归属配置。进一步编辑生成规则后，可使用 `configure_connectivity.py` 和 `configure_adreno_symlinks.py` 重新检查归属；原文件仍本地保留。不要重新引入强制 HWUI Vulkan 等已撤回的图形绕过。

## 4. 检查与编译

```bash
python3 "$port_root/tools/check_local_inputs.py" --root "$android_root"
cd "$android_root"
python3 "$port_root/tools/audit_copy_conflicts.py"
python3 "$port_root/tools/audit_blob_install_paths.py"
bash "$port_root/scripts/build-pixelos.sh" "$android_root" 16
```

构建入口实际执行 `lunch custom_m2381-bp4a-userdebug`、`m pixelos`，先核验本地输入和必需平台补丁，无刷机命令。完整校验会读取数 GB 文件。

## 5. 启动边界

默认构建产物不能自动复现现有真机的诊断启动链：当前依赖匹配的 ramdisk、模块、bootconfig、AVB 链及 metadata 脚本。不要把 OTA 构建成功解释为整包可安全更新。`diagnostics/README.md` 说明现有依赖和历史工具，本次未提供一键刷机入口，也未修改手机。

设备树默认内核现已对齐当前诊断候选的 B 槽去 KernelPatch 副本，原始带补丁备份保留在机主本地。来源与摘要见 `docs/local-inputs.md` 和 `provenance/kernel-lineage.json`。内核一致仍不等于 ramdisk、AVB 与 metadata 启动链全部自动配置完成。

## LineageOS 与其他衍生 ROM

同一设备公共配置现有 `lineage_m2381` 与 `custom_m2381` 产品入口。LineageOS 使用自身分支的 release token 和 `m bacon`；其他 ROM 使用自己的构建约定。不要对所有 ROM 执行本页的 `m pixelos`。迁移范围及尚未执行的 LOS 编译验证见 [ROM 兼容性](rom-compatibility.md)。
