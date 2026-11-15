# 许可证、来源与发布边界

本仓库新增的设备适配脚本、文档和独立实现按根目录 `LICENSE`（Apache License 2.0）提供，文件另有声明时以文件声明为准。保留的 AOSP、LineageOS、Qualcomm 及其他第三方文件保留各自版权与许可；根目录许可证不覆盖、也不重新授权原厂专有输入。补丁所修改的上游代码继续受上游许可约束。

设备树最初参考 Meizu 21 Note / M2468 的 LineageOS 23.2 设备树，随后修改为 Meizu 20 的分区、内核输入、服务、显示与相机配置：

- 参考镜像：<https://github.com/meizu-sm8550-kernel/android_device_meizu_m2468>，参考提交 `e40d9f72ba5169a59322532990a1df944bab6f5d`。
- 参考树记载的更早来源：<https://cnb.cool/AstralSpun/android_device_meizu_m2468>，提交 `b82127689b3f7aa7a09c51b3af8b8a3140eeaa17`。
- PixelOS：<https://github.com/PixelOS-AOSP/android_manifest>，`sixteen-qpr2`，manifest 提交 `e37ff60b6e27a3c51f3c6ab01a42473bec7aa2a2`。
- 平台补丁涉及 Android Open Source Project、LineageOS 与 PixelOS；文件头和补丁上下文中的版权声明保持原样。
- 历史 KernelPatch 还原工具参考 bmax121/KernelPatch `0.12.0`，提交 `57d487090add7e25e98cfb8d569d999c14f30352`；本仓库不包含 KernelPatch 二进制。

`provenance/upstream-device-reference.json` 是参考树自身的元数据：其中 m2468 指纹/相机模块的编译或运行结论不代表 M2381 经过同样验证。M2381 当前仍使用原厂内核和模块。

`provenance/local-inputs.json` 记载的是开发时观察到的输入摘要，部分 vendor 文件已做适配修补；它既不是官方固件签名证明，也不是二进制发布许可。本仓库现随附该固定版本的内核、模块、厂商二进制与受限配置，以便使用同一套输入构建；这些文件保留其原有版权及许可，不转为 Apache 2.0 开源代码。内核及其他组件的原有许可义务同样保留。原始带 KernelPatch 的备份、密钥和设备用户数据不随附。

已有 WSL 构建树曾删除 `.repo` 元数据，因此无法导出完整的 `repo manifest -r` 锁定清单，也不能证明枚举出了该树的每一项历史源码差异。归档包含已核对的设备树、vendor 输入、六项平台补丁和历史环境改动说明；不宣称能逐字节复现旧整包。
