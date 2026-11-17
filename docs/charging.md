# M2381 充电适配

## Health 信息

设备 `health/` 基于 QTI AIDL Health 入口和 AOSP `libhealth_aidl_impl`，
产品选择 `android.hardware.health-service.m2381`，保留关机充电入口与 UCSI
伪电源过滤。原厂 Health 的三项安装规则被替代，原始输入仍保留。
服务使用 Android 17 Health V5，不可直接复制到缺少匹配接口的旧分支。

- fuel gauge 的 `charge_counter` 从 mAh 转为接口要求的 µAh，独立查询与回调一致。
- `65535 * 60` 秒的无效估时映射为未知 `-1`。
- USB 在线、输入电流及限流均 0、电池净放电且无无线/dock 供电时报告
  Not charging；不因瞬时负载、满电降流或读失败误判。
- SystemUI 快充分界资源统一为 20W。界面依据最大供电能力分类，不表示实时功率。

Health 只读取节点，不改变温控、限流或 PD。重新生成 vendor 规则后可用本工具仓
`tools/configure_health.py /path/to/android` 恢复模块归属。

## PD 枚举限流兼容

已知原厂模块在电脑 PD 连接重启后会接受 Gadget 枚举的 2mA/500mA 请求，
导致固件 USB_ICL=0，USB 在线但电池持续放电。兼容副本仅把 `usb_psy_set_icl`
的类型掩码从 `0x4a` 改为 `0x0a`：保留 SDP/CDP 枚举限流，PD 由固件协商及
既有温控投票管理。不设置固定电流，不修改 PD 合约、温控、充电终止或看门狗。

这是一项原厂模块二进制兼容修正。`modules_prebuilt` 与 `proprietary` 原始输入
保持不变，产品安装 `vendor/meizu/m2381/compat/vendor_dlkm/lib/modules/qti_battery_charger.ko`。
方法及输入/输出摘要见 `provenance/charging-pd-icl.json`。

```bash
python3 /path/to/android_manifest_meizu_m2381/tools/configure_pd_icl.py --root /path/to/android
# 缺少兼容副本时，从已知原始输入复现：
python3 /path/to/android_manifest_meizu_m2381/tools/configure_pd_icl.py --root /path/to/android --apply
```

工具核对架构、节位置、原指令和整文件前后 SHA-256；未知输入和冲突输出均拒绝。
不能套用于其他机型或不同版本。当前内核允许此模块加载；严格模块签名环境不能
直接照搬。将来有匹配源码时应在源码实现并重新验证电源类型和热管理。

## 验证

Android 17 构建 shell 中执行：

```bash
m android.hardware.health-service.m2381 SystemUIOverlayM2381 m2381_health_policy_test
out/host/linux-x86/nativetest64/m2381_health_policy_test/m2381_health_policy_test
```

Health 主机 6 项测试通过，覆盖故障输入、恢复、满电/负载、缺失节点、估时哨兵、
单位与溢出。真机核对过 HealthInfo、独立查询和 BatteryService；模块兼容修复后
四次保持电脑连接重启均实际取电，限流保持协商的 3A，ADB 数据校验通过。
快充头切回电脑未复现零限流；测试时接近满电，没有验证高功率或更高电压合约。

低电量快充、普通 SDP/CDP 与长期满充/温控仍需单独回归。
旧安装若残留 metadata 临时模块/Health/RRO 挂载，安装正式包含修复的镜像后需撤销，
避免覆盖新文件；运行中覆盖磁盘文件不能替换已加载内核模块。
