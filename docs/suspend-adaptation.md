# M2381 拔线熄屏重启与待机路径适配

## 已确认的故障

2026-11-16 真机离线采集确认：USB 拔线、熄屏后发生的是内核重启。
进入 `suspend(s2idle)` 后，约 23 秒未继续喂狗，QCOM Apps Watchdog
报告 `Suspend in progress`、`Watchdog work is pending at CPU(2)`，
随后在 `qcom_wdt_bark_handler`、`qcom_wdt_core.c:853` 触发 BUG 和 panic。
此前的 WLAN transmit queue timeout 只能作为线索，尚不能证明 WLAN 是根因。

USB 连接电脑时控制器持有唤醒锁，不能用插线时不重启证明待机稳定。

## 设备树修正

通过 Android 标准 `/sys/power/mem_sleep` 选择内核已提供的 `deep`。
配置在 `android_device_meizu_m2381/init/init.m2381.rc`：

```rc
on init
    write /sys/power/mem_sleep deep

on property:init.svc.kernel-post-boot=stopped
    write /sys/power/mem_sleep deep
```

厂商 `init.kernel.post_boot-kalama_*.sh` 会写入 `s2idle`，服务由
`sys.boot_completed=1` 启动。仅在 early-init、init 或 boot_completed
设置会被其覆盖。服务停止事件保证设置在脚本退出后执行，并覆盖该服务再次运行的情况。
不修改 AOSP、厂商原始脚本或内核，不关闭看门狗，也不循环写入节点。

这是当前原厂 5.15.119 内核与诊断启动环境下的待机路径规避，尚未修复
s2idle 内部阻塞的底层驱动。更换内核或撤销已有 CPU idle 诊断配置后需重新验证。

## 真机交付和验证边界

当前手机仍走 `/metadata/bootdiag/init.round48.rc` 诊断入口，本轮将等价触发器
安装在该入口，保存原件并核验 SHA-256；没有重刷 ROM 或修改用户数据。
设备树修正需后续构建镜像安装后才能通过正式 vendor init 路径交付，不能将
手机诊断入口已生效等同于完整新镜像已刷入。

- 临时选择 deep 的先前对照：约 17 分钟拔线熄屏，27 次进入/退出记录，
  成功挂起计数增加 21，包含 RTC、ADSP 和电源键唤醒，没有新 panic 或重启。
  仍有 6 次挂起失败/中止，不能声称全部尝试成功。
- 安装服务停止触发器后的正常重启：日志确认触发器在约 17.17 秒成功写入，
  开机完成、kernel-post-boot 已停止后多次读取均为 `s2idle [deep]`。
- 本轮开机时 watchdog disable=0、console_suspend=Y，未关闭保护。
- 最终配置下的拔线熄屏回归与长时间、低电量、充电切换等场景仍需验证。

原始日志、设备标识和备份保留于工作区私有 `.local-flash/`，不纳入公开仓库。
