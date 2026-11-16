# 分仓接入后的编译验证

> 2026-11-16 平台隔离迁移：下文的平台补丁和 remove-project 描述是历史构建记录。当前 Android 17 使用官方 shim、设备 linker 配置、预编译内核头接口与产品级源码选择，不再应用六项平台补丁或全局移除 HAL 项目。操作与验证边界见 [平台隔离](platform-isolation.md)。


2026-11-15，在 WSL `/home/zhaiy/pixelos17` 执行构建入口：

```bash
export SOONG_INCREMENTAL_ANALYSIS=false GOMEMLIMIT=32GiB GOGC=30
bash /mnt/c/Users/zhaiy/Documents/Project/meizu20-m2381/android_manifest_meizu_m2381/scripts/build-pixelos.sh /home/zhaiy/pixelos17 12
```

这是复用已有 `out` 的增量整包构建，重新运行 Soong 和 Make 解析，不能作为空目录全量构建或真机验证的证据。目标为 `custom_m2381-cp2a-userdebug`。

## 实际结果

- 首次解析失败：电源 HAL 的完全限定依赖 `//hardware/qcom-caf/sm8550:libdisplayconfig.qti` 无法通过 namespace imports 重定向。
- 设备仓提交 `45581a6` 使用上游 `QCOM_SOONG_NAMESPACE := vendor/qcom/opensource/display` 配置入口解决依赖，未新增平台补丁。
- 修复后 Soong、Make、镜像生成、上游 `build-manifest.xml` 和 OTA 打包通过，构建退出码 0，耗时 12 分 38 秒。
- 生成的 ZIP 全部成员 CRC 校验通过。
- 日志仍有 `TARGET_SCREEN_WIDTH is undefined, assuming 1080p` 警告。

产物：`/home/zhaiy/pixelos17/out/target/product/m2381/PixelOS_m2381-17.0-20261115-1343.zip`

大小：3451400079 字节。

SHA-256：`c9e7301ca63c57d2c8981d4c99ac47e5a41e4bfb8cb413f53c000d89a1735f12`

日志：`/home/zhaiy/m2381-split-build.log`。

## 验证边界

构建日志显示 32/64 位 `libdisplayconfig.qti.so` 来自 `vendor/qcom/opensource/display/services/config/src` 并被安装到 vendor。它替换了原厂副本，运行时与原厂显示服务的 ABI 和行为兼容性仍需真机验证。

上述首次构建当时没有进行刷机。后续真机验证见下节；已有诊断启动链、SELinux permissive 等限制继续适用，不能据此判定通用 OTA 可直接安装。

当前 Android 17 平台补丁组仍有六项；本次没有证明其中每一项都不可替代，也没有完成零平台补丁的迁移。

## 2026-11-16 真机刷写验证

刷写前发现增量产物的 Health init 配置仍指向旧 QTI 文件名，而实际安装的是
`android.hardware.health-service.m2381`。设备仓提交 `04f5bc5` 将 init 和 VINTF
文件改为独立名称，重新执行整包构建，退出码 0。确认 vendor 只保留新的 Health
init 配置，服务命令指向设备自有可执行文件。本次没有新增 AOSP 修改。

取得并校验当前 B 槽启动、AVB、recovery、dtbo、misc 和完整 8 GiB super 备份，
另备份 metadata 诊断目录。沿用当前已验证的 boot/init_boot/vendor_boot，针对新
系统镜像重新生成 AVB 父子链，分别验证预期密钥及完整哈希树。

通过官方 fastbootd 写入 B 槽七个逻辑分区，不擦除 userdata；在诊断 recovery
按更新后的 super extent 回读七分区 SHA-256，全部与候选一致，两个 metadata
槽的分区布局一致。清理旧 Health/UI 临时挂载，保留原 PD 模块挂载与诊断启动。
写入五个启动/AVB 分区，恢复刷前 recovery 后启动；五分区运行时回读同样一致。

运行结果：

- `sys.boot_completed=1`，新启动 ID，B 槽；系统构建时间为 2026-11-16 00:07:33 CST。
- SurfaceFlinger、显示 composer、Zygote、SystemUI 正常运行；唤醒后截图显示锁屏。
- Wi-Fi 已连接，网络具有 VALIDATED 状态。
- 新 Health 服务已注册，运行文件哈希与源码编译产物一致；电量 100%，状态 FULL，
  USB 输入限流 3 A，采样输入电流 56 mA。满电采样不能证明大功率充电能力。
- crash 日志仍有 `vendor.dpmd` 缺失 `android::hardware::Parcel::setData` 和
  `slim_daemon` 缺失 `__emutls_get_address`；尚未解决，不能认定全功能通过。
- 触摸、相机、通话、移动数据、指纹和长期稳定性未完成验证。

备份、候选清单、刷写/回读及运行日志保存在工作区 `.local-flash/split-20261115/`，
含设备私有信息，不纳入仓库。此次是保留诊断启动链的定向刷写，不是通用 OTA 安装验证。
