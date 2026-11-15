# 历史启动诊断材料

这里保存离线打包/核验工具、汇编诊断小程序源码，以及当前真机第 47 组启动脚本文本。它们用于解释现有系统如何启动，**不是正式 recovery 或通用刷机方案**。普通构建不自动安装这些文件。

`reference-round47/init.round47.rc` 的已观察 SHA-256 为 `5d9bed4d08287e24a92af8497046209139fc5e6593f342862b2c5520ae2c7681`。这套脚本在 `/metadata/bootdiag` 下运行，包含 staged init、模块 blocklist、vendor modprobe 包装、CPU idle state1 禁用、日志、ADB 准备及启动超时监测。正常完成启动会停止超时服务。图形三项绕过已从该文件撤回。

仅有这些 rc/sh 文本不足以复现整条启动链：还需要先前验证的 boot/vendor_boot ramdisk、匹配 DTB/模块、诊断 helper（busybox、deadline 等）、AVB 链、metadata 文件权限和本机 ADB 公钥。这里没有公钥/私钥、诊断 helper 二进制、原始设备日志或镜像；不能在空白设备上直接调用历史脚本就宣称可启动。

`vendor-modprobe.round47.sh` 派生自带专有声明的原厂脚本，因此保留原声明，现按固定依赖随仓库提供。在恢复普通原厂输入后，运行 `python3 tools/materialize_diagnostics.py --apply` 可按 `provenance/diagnostic-inputs.json` 的插入记录重建，并核验原始/最终摘要。这是 5418 项基础输入之外的一个派生诊断文件。

`tools` 中的准备器均为历史诊断步骤，参数/组号对应当时输入；同目录 Python 导入关系保留。`scripts` 是第 19/22/23 组旧工作流归档，默认需要旧日志/候选镜像目录，因此只作为历史参考，不是本次公开构建入口。脚本添加了显式启用门槛，默认退出，以免误当成通用流程。历史日志和镜像未纳入仓库。

`source-snapshots/build-manifest_xml.mk` 记载旧树失去 `.repo` 后的本地妥协，正常构建必须保留 repo 版本信息，不应用此快照。重建的音频 UAPI 头仅能说明历史编译做法，不能作为真实内核 ioctl 合约。

后续发布前需把确实必要的启动修复迁移到正常 init/设备配置中，验证 enforcing、去除 root ADB 和诊断依赖，并单独验证 recovery、双槽更新及失败恢复。

内核还原工具本次已重新执行，输出与第 47 组已保留候选 boot 内的内核逐字节摘要一致；当前默认 Image 已切换为这份去补丁结果，并随 LFS 提供。旧带补丁备份仍在机主本地。具体来源链见 `provenance/kernel-lineage.json`。
