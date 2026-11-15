# 分仓接入后的编译验证

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

本次没有刷机或启动验证。已有诊断启动链、SELinux permissive 等限制继续适用，编译成功不能据此判定整包可直接刷入。

当前 Android 17 平台补丁组仍有六项；本次没有证明其中每一项都不可替代，也没有完成零平台补丁的迁移。
