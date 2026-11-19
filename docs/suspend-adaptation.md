# M2381 待机路径

当前原厂 5.15.119 内核在拔 USB、熄屏进入 s2idle 后曾因挂起阻塞触发 QCOM
Apps Watchdog panic。WLAN timeout 只是线索，尚未证明是根因；连接电脑时
控制器持有唤醒锁，不能用插线稳定代替离线待机验证。

设备 `init/init.m2381.rc` 通过标准 `/sys/power/mem_sleep` 选择已有的 deep：

```rc
on init
    write /sys/power/mem_sleep deep

on property:init.svc.kernel-post-boot=stopped
    write /sys/power/mem_sleep deep
```

厂商 post_boot 脚本会改回 s2idle，因此还需在服务停止后设置。
此方式不改公共源码、原厂脚本或内核，不关闭看门狗，也不循环写节点。
它规避当前环境的 s2idle 路径，尚未修复底层驱动阻塞。

init 模块构建及 host_init_verifier 通过；正常重启后确认选择 deep，拔线熄屏
回归记录 28 次成功挂起及 2 次失败/中止，无新看门狗 panic 或重启。
这不是全部挂起场景通过，也不是长时间功耗结论。
更换内核、去除已有 CPU idle 诊断配置或收敛启动链后需重新测待机与唤醒。


2026-11-20 标准启动链回归：已去除诊断启动参数、metadata bind mount 和 CPU idle
限制，八个 CPU 的 state1/disable 均为 0；正常启动后选择仍为 deep。
用户拔 USB、熄屏静置约五分钟后重新连接，boot ID 保持不变，pstore 为空。
挂起计数从 success=0/fail=0 增至 success=8/fail=2；两次中止在 freeze 阶段，
last_failed_errno=-16，未触发 panic。日志可见 deep entry/exit 及 RTC/WLAN/基带
唤醒。此项证明解除诊断限制后的短时离线回归通过，不能当成长时间功耗结果。
