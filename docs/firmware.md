# 固件与驱动版本

## 固定基线

本项目直接随附本次适配所用的文件，克隆并获取 LFS 对象后即可使用这套固定驱动。使用者当前手机上的 Flyme 版本不会决定构建时使用哪套驱动；设备上保留的 bootloader、DTBO、modem 等固件则仍需与所选启动链和硬件兼容，不能据此宣称任意底包都可刷。

原始设备属性和随附 vendor/build.prop 记录如下：

| 项目 | 值 |
| --- | --- |
| 设备原系统显示版本 | Flyme 12.7.0.0A |
| Build incremental | 1764128685 |
| Build fingerprint | `meizu/meizu_20_CN/meizu20:16/BQ2A.251016.001-BP2A.250605.031.A3/1764128685:user/release-keys` |
| 系统 Android 版本 | 16 |
| vendor Android / SDK | 13 / 33 |
| Vendor security patch | 2023-10-01 |
| 内核 | 原厂来源 Linux 5.15，B 槽去 KernelPatch 副本 |

机器可读版本在 `provenance/firmware-baseline.json`。这里只导出构建属性，没有序列号、IMEI、ADB key 等设备身份信息。

屏幕参数曾参考官方 **Flyme 12.6.0.0A framework-res.apk**；该来源只用于框架几何比对，不是这套驱动版本的名称。官方入口为 <https://foru.flyme.cn/firmwarelist-195.html>，目前没有一份已核验完整包摘要、能证明包含所有随附输入的官方 OTA，因此不提供猜测出来的“下载此包即可完整复现”链接。

## 使用不同驱动版本

“复现当前适配”直接使用随附输入。若希望换成另一版 Flyme 的驱动，那是新的适配基线，可能涉及不同服务、符号依赖、内核模块和固件 ABI。可先只读比较：

```bash
python3 tools/compare_firmware_inputs.py   --source /path/to/extracted-partitions   --report local/firmware-comparison.json
```

工具汇总所有 5039 项 vendor 输入，区分已修补版本、已知修补前版本、不同版本和缺失项，不在第一个不同文件处停止，也不会导入或改写文件。未知或缺失项以非零状态退出。这是差异清单，不是兼容性认证。

更换版本需单独建立清单/分支：配套使用内核、DTB、339 个模块及用户态驱动；重新核对 ELF 依赖、VINTF、启动配置和图形指令修补；完成编译和真机回归后才标为支持。不允许将已知版本的 EGL/Vulkan 指令偏移强套到未知 `.so`。不同版本可能最终兼容，但不能仅凭文件名相同保证。

## 可复现性的边界

现在驱动、模块和配置可以按固定文件及摘要复现，不再依赖原作者私有工作区。旧 Android 源码树曾丢失完整 repo 元数据，因此仍没有完整的全树 revision lock；本次未新同步完整 LineageOS/PixelOS 源码并全量编译，也未重新刷机。现有诊断启动链尚未全部收敛到正式设备配置。它们是后续要补齐的工作，和驱动是否随仓库提供分别记录。
