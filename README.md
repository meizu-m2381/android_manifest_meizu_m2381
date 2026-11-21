# android_manifest_meizu_m2381

魅族 20（`m2381`）的 local manifest、构建入口和兼容检查工具。
当前基线为 PixelOS 17 / Android 17，设备、vendor、内核分别由独立仓库提供。

## 同步与构建

先将本工具仓克隆到 Android 源码目录之外，再在独立源码目录执行：

```bash
repo init -u https://github.com/PixelOS-AOSP/android_manifest.git \
  -b seventeen --depth=1 --manifest-depth=1 \
  --partial-clone --clone-filter=blob:none \
  --git-lfs --no-clone-bundle --no-tags --platform=linux
mkdir -p .repo/local_manifests
cp /path/to/android_manifest_meizu_m2381/local_manifests/*.xml .repo/local_manifests/
repo sync -c -j4 --no-clone-bundle --no-tags
bash /path/to/android_manifest_meizu_m2381/scripts/build-pixelos.sh "$PWD" 12
```

需要先安装上游要求的 Linux 构建依赖及 Git LFS，并下载完整 LFS 对象。
构建脚本核验固定输入、兼容副本和目标产品，再执行构建。
详细步骤见 [构建指南](docs/build.md)。

## 兼容方式

Android 17 使用官方 LineageOS shim、固定摘要的 ELF 依赖修补、设备 linker 配置
与上游预编译内核头接口。HAL 源码选择只作用于 M2381 产品；local manifest
保留上游项目，不要求修改公共 AOSP、Aperture 或冻结 VNDK 源码。
兼容范围与验证边界见 [平台隔离](docs/platform-isolation.md)。

## 文档

- [当前功能与交付限制](docs/status.md)
- [固定输入与内核来源](docs/local-inputs.md)、[固件版本](docs/firmware.md)
- [兼容修补](docs/patches.md)、[迁移其他 ROM](docs/rom-compatibility.md)
- [检查命令](docs/validation.md)、[Recovery/OTA 与标准启动链](docs/recovery-ota.md)
- [充电](docs/charging.md)、[待机](docs/suspend-adaptation.md)、[指纹](docs/fingerprint-adaptation.md)、[圆角](docs/corner-calibration.md)
- [移动网络与信号刻度](docs/mobile-network.md)
- [自动亮度与原厂校准](docs/auto-brightness.md)
- [抬起亮屏](docs/pickup.md)、[双击亮屏](docs/double-tap.md)、[AOD与显示链路](docs/display.md)
- [硬件服务归属、SLIM、VSYNC与震动修复](docs/service-ownership.md)

标准启动已去除诊断依赖，Recovery 完整包安装、Android OTA 跨槽合并、fastbootd 和 USB 功能切换已通过真机检查；
修正包已重复安装与合并，ARM/ARM64 硬件编码及普通重启通过；首次解锁后的全部硬件和长期回归仍需验收。发布和安装前请核对功能状态及 [来源与许可](NOTICE.md)。
