# 固定版本的构建输入

内核、模块、厂商驱动和原厂配置已随仓库提供。克隆后执行 `git lfs pull`，即可使用和当前适配相同的文件，不要求使用者自己的 Flyme 固件恰好具有相同版本。

## 清单

`provenance/local-inputs.json` 是当前构建使用的 5436 项输入：

| 类别 | 数量 | 内容 |
| --- | ---: | --- |
| `vendor-input` | 5057 | vendor/odm/dlkm、system_ext IMS/电话音频桥预编译输入及两项 SELinux 输入 |
| `stock-kernel-input` | 342 | 已还原内核 Image、两个 DTB 输入、339 个 `.ko` |
| `restricted-stock-config` | 37 | 保留原专有声明的 init/VINTF 文本配置 |

清单包含生成规则引用但产品未启用的历史模块输入，不表示所有文件都安装到镜像。

`provenance/bundled-inputs.json` 进一步包含 40 项适配前原始文件。每项记录路径、大小和 SHA-256。内核/驱动主体用 LFS 储存；受限文本保留原字节和声明。原厂版权与许可不因纳入仓库而变化。

```bash
# 在设备、内核和 vendor 各仓库获取 LFS 对象后，在本工具仓执行：
python3 tools/check_bundled_inputs.py --root /path/to/android
python3 tools/check_local_inputs.py --root /path/to/android
```

若文件仍是 LFS 指针，核验会提示拉取 LFS 对象。发布仓库时必须确保服务器同时有这些对象；只推送 Git 指针不能完成依赖分发。单文件 SHA-256 用于识别输入，不等于兼容所有固件版本，也不等于官方固件签名认证。

## 修补前与修补后

`vendor/meizu/m2381/proprietary` 提供当前构建使用的版本。与原始提取结果不同的 40 项文件，其原始版本放在 `vendor/meizu/m2381/original-inputs/<分区相对路径>`。其他输入没有发生内容变化，不重复存一份。

25 项文本差异记录于 `patches/vendor-text-fixups.json`；12 项 tinyxml2 ABI 修正以及三项 EGL/Vulkan 修正在 `tools/`。已在隔离目录从修补前输入重建并逐项核对最终摘要。对未知驱动版本不能照搬机器码偏移，处理方式见 [固件版本说明](firmware.md)。

## 内核来源

当前 `TARGET_PREBUILT_KERNEL` 指向 `device/meizu/m2381-kernel/Image`，SHA-256 为 `0f082b0fa6d21007a24b6a11976a08867be6612e65cfe1db29bbc08e2462648e`。它是当前设备树选择的去 KernelPatch 副本。

原始设备备份的 A/B 内核带有历史 KernelPatch 0.12.0。本项目按该版本的已知还原流程恢复 B 槽入口并移除追加内容，保留 `tools/restore_kernelpatch_012.py`、来源摘要及结果摘要；带 root 补丁的 A/B 原始备份留在原机主本地，不随仓库提供。`Image` 现已对齐还原副本，配套模块不变。没有厂商官方原始包摘要，不能把该过程描述为官方原包身份认证。见 `provenance/kernel-lineage.json`。

## 更换输入

vendor makefile 直接维护，不提供继承自其他机型的提取或规则生成入口。
要替换固件版本，先运行 `compare_firmware_inputs.py` 查看完整差异，再建立新输入清单、移植修正、验证 ABI 和硬件功能；不要覆盖当前固定基线后跳过摘要校验。

## 自编译替代

Wi-Fi 服务、震动 HAL 和资源覆盖已提供源代码；当前内核、GPU、相机等仍依赖预编译输入。M2468 的内核参考不能直接作为 M2381 的等价替代。替换内核需要匹配的 DTS、配置、UAPI/模块 ABI 和真机验证；替换专有用户态驱动同样需要兼容实现。
