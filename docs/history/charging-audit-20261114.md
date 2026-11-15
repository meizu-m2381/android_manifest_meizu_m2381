> 历史核查记录（已去除启动标识）。以 当前状态（原工作区：`../status.md`） 为准；文中日志和截图留在原本地工作区，未随本仓库发布。不是刷机指南。

# PixelOS 电脑充电与状态显示核查（2026-11-14）

本轮只读取真机数据、历史日志与源码；未刷机、重启、修改充电节点或温控。原始诊断保存在本地忽略目录 `logs/charging-audit-20261114/`，不提交设备私有转储。

## 已确认的现象

| 场景 | 实测证据 | 能得出的结论 |
| --- | --- | --- |
| 历史不取电 | `usb_online=1`、`real_type=PD`、`vbus≈5.05V`、`ibus=0`、`usb_icl=0`，同时 `ibat<0` | 确实接入电源但电池仍放电，不只是文字显示错误 |
| 历史持续掉电 | 一段启动内 10–2653 秒，电量 48%→46%，剩余容量 2146→2048 | 故障持续存在，并非单次电流采样抖动 |
| 当前电脑连接 | 用户确认手机连着电脑；USB 输入约 1.77–1.87A、电池净充入约 1.66–1.76A，电量 89%→91%→92%→97%→100% | 当前确实可以通过电脑充电，不能认定这个系统完全无法充电 |
| 当前充满 | `status=Full`、`capacity=100`、`time_to_full_now=0`，USB 输入降到约 0.097A | 充满后低电流与此前未充满时输入为零需要区分 |

历史日志来源是 `/sdcard/mbattery_charger/mbattery_charger_log_2026_11_12`。手机多次开机时间回退到同一天，因此按日志中的启动秒数回落分段，不按墙钟推断先后时间或对应哪轮镜像。原始快照 `mpower-history.txt` 和分段摘要 `charging-history-segments.json` 中，段 0–7 不取电，段 8–11 开始正常取电；段 8 开始时输入约 2.81A、上报限流 3A。它们之间的接线、充电头、重启变化尚未确定。

## 为什么显示四十多天

故障时 `TTF=3932100` 秒，恰好等于 `65535 × 60`，即 45 天 12 小时 15 分钟。正常取电时 TTF 恢复到正常分钟数，而不适用的 TTE 又变成同一个 3932100。这强烈提示它是 0xffff 分钟的“未知/不适用”标记，但其固件编码来源尚未通过固件分析证实。

已核对的 AOSP 源码路径：

1. `system/core/healthd/BatteryMonitor.cpp` 从 `time_to_full_now` 读取秒数。
2. `frameworks/base/services/core/java/com/android/server/BatteryService.java` 转发 HealthInfo 的剩余时间。
3. `frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java` 的 `computeChargeTimeRemaining` 优先接受非负的 HAL 剩余时间，没有识别该设备的异常标记。
4. SystemUI 的 `KeyguardIndicationController` 将时间格式化显示。

当前安装的是原厂 QTI health 服务，不能仅靠 AOSP 参考实现断言这个二进制内部的读取方式；其内部完整调用链尚未验证。已经能够确认驱动给出异常正数，显示时长与之精确对应，而框架上述路径会接受该值。修复应在本设备 health 适配中将经确认的无效值转为未知（标准值 -1），而不是用任意天数阈值掩盖，也不能将文字正常当作充电恢复的证据。本轮尚未替换或验证修改版服务。

## 为什么电脑连接也显示快速充电

当前系统上报最大电流 3,000,000µA、最大电压 5,000,000µV，即最大功率 15W。SystemUI 实测 `mChargingWattage=15000000`、`mChargingSpeed=2`，电池广播中 `oem_fast_charging=false`。

`frameworks/base/packages/SettingsLib/src/com/android/settingslib/fuelgauge/BatteryStatus.java` 按最大电流和最大电压计算功率，再与快速充电阈值比较。本机资源查询得到旧阈值 7.5W、v2 阈值 20W；当前 15W 被判为快速与旧阈值吻合。这里使用的是上报的最大功率，不是此刻的实测输入功率，因此故障时也可能仍显示快速充电。

当前 Type-C 为 `sink/device`、`power_operation_mode=usb_power_delivery`，对端声明支持 USB PD，UCSI 电源也上报 5V/3A。电脑的 USB-C PD 接口可以提供这个档位，不能只因它是电脑就断定不可能快速充电；也不能仅凭 3A 声明认定电脑已经实际输出 3A。

## 尚未确定的不取电触发原因

不取电时 ICL 读数为零是定位线索，不能单凭它证明是谁下发了零限流。尚无证据证明必须修改内核，或证明缺少某个 Flyme framework 调用就是原因。

另一个已确认的集成问题是两套 USB 服务同时启动并声明：

- 源码 AIDL：`android.hardware.usb-service.qti`、`android.hardware.usb.gadget-service.qti`。
- 原厂 HIDL：`android.hardware.usb@1.2-service-qti`、`android.hardware.usb.gadget@1.1-service-qti`。

USBManager 使用 AIDL，但 `current_functions_applied=false`，旧服务也在运行。重复服务是应处理的 USB 集成问题；目前没有隔离实验能证明它导致输入电流为零。不能把清理重复 HAL、修复 USB 控制页面或修复快充文字直接称为充电故障已修复。

另外，当前 `charge_counter=4386`，而 `charge_full=4386000`；充电中计数变化速度也更像 mAh，提示前者可能缺少标准 µAh 所需的 1000 倍换算。该异常需在 health 替换时单独核对，不是本轮“45 天”显示来源的已证实解释。

## 验证边界与后续定位

本轮已完成真机多点采样、历史日志对照、Type-C 角色核对、SystemUI 状态/资源查询和源码路径核对。ADB 初始离线在 `adb reconnect offline` 后恢复；此操作没有改变充电节点。当前启动 ID 为 `[boot-id omitted]`，本轮没有主动重启。

截至首轮核查，尚未复现由正常取电变为零输入的过程（后续满电拔插实验见文末），也未完成以下验证：

- 同一根线、同一电脑接口下的插拔/重启对照，以及失败瞬间的 UCSI、PMIC 与充电日志。
- AIDL/HIDL USB 服务清理后的功能与充电回归。
- 设备 health 对无效 TTF 和 charge counter 单位的适配、编译与真机验证。

优先确认恢复前是否换口、换线、接过充电头或重启。复现时同时记录 USB 实际电流、净电池电流、电量趋势和 Type-C 状态；保留正常对照。充满后的低电流不能用来复现此前故障。不强设 ICL、不关闭温控，避免改变现场并绕过供电协商。

## 用户补充与后续检查

用户随后两次确认：此前不取电到恢复之间，**接过快充头，再接回电脑**。这使“不同电源连接触发充电状态重新初始化”成为重点假设，但不能证明快充头是恢复的充分条件，也不能排除期间其他操作的影响。

后续读取同一次开机的状态，启动秒数约 10228 秒，仍为电脑 USB PD、100%/Full、ICL 3A。本地反汇编所用 `qti_battery_charger.ko` 和 `ucsi_glink.ko` 的 SHA-256 与手机 `/vendor/lib/modules/` 中对应文件一致；这只核对了磁盘文件，不证明当前加载映像的内存状态。

源码 AIDL `vendor/qcom/opensource/usb/hal/Usb.cpp` 的 `limitPowerTransfer` 通过 `restrict_cur`/`restrict_chg` 控制限制；当前 `restrict_chg=0`，因此没有证据证明此限制正在阻断充电。该服务在 Type-C 电源模式变化时也会修改 USB gadget 的 `MaxPower`/`bmAttributes` 描述符，不能把描述符的零值等同于充电硬件 ICL 为零。当前读数为 `900`/`0x80`，尚未得到描述符变化与历史故障之间的因果证据。

为捕获断线期间状态，启动临时的 300 次只读采样，每次读取后等待一秒，输出 `/data/local/tmp/charging-replug-20261114.txt`，请求用户同一电脑接口拔插，期间不接充电头。记录覆盖 USB online/type/ICL/电流/电压、电池状态/电量/电流/TTF、Type-C 角色与电源模式、restrict_chg 及 USB 描述符。读取开销及断线时系统休眠使实际采样间隔超过一秒，总记录约 520 秒；原先向用户估计的 5 分钟偏短。该实验用于检查重新连接状态；满电下不能仅凭小电流判断失败。未修改充电设置。

## 同接口拔插结果与重启对照准备

用户确认同接口拔插完成、画面正常。已取回完整 300 次记录，结尾有 `COMPLETE`；本地文件为 `replug-result.txt`，另保存 `replug-dmesg.txt`、`replug-logcat.txt` 和 `replug-usb-state.txt`。同一启动 ID 未变。

| 启动秒数 | 状态变化 |
| --- | --- |
| 10394.50 | PD，输入限流 3A，电池 100%/Full |
| 10744.29 | 拔线：online=0、输入限流为零、Discharging |
| 10755.50 | Type-C 暂报 1.5A，尚未 online |
| 10770.06 | 重连：online=1、PD、输入限流 3A、输入约 1.77A，短暂报 Charging |
| 10774.96 | 电池重新报 Full，输入电流已降到约 0.39A |
| 10805.36 | 输入限流变为零、输入电流为零；电池仍报 Full、TTF=0 |
| 10914.04 | 仍 online/PD、ICL=0，电池电流约 -194mA，仍报 100%/Full |

整个实验中 `restrict_chg=0`，USB 描述符读数维持 `900`/`0x80`。这次成功记录了“已重连并取电，随后零输入”的变化，但**尚不能将满电下的零限流判为此前未满电不充电的同一故障**；需要观察再充阈值或在非满电条件下复现。也没有出现 3932100 秒异常 TTF。

用户提出可能与“重启后第一次插电脑”有关，下一步按此条件对照：拔线后在手机中重启，进桌面后直接接同一电脑接口，期间不接充电头。电脑端已准备以启动 ID 变化识别新开机，连接后立即抓取 dmesg/logcat，并进行约两分钟以上的电池/USB 采样；测试结果尚待取回。没有为了该实验刷机或改充电参数。

## 重启后首次连接电脑的实测结果

用户确认已拔线重启、进入桌面并直接接回电脑。新启动 ID 为 `[boot-id omitted]`，USB 日志中约 23.945 秒首次出现连接事件，内核约 24.121 秒记录 `usb_in=1`。这与用户描述的拔线重启后接入一致。

自动采样已结束，共 41 个成功样本，覆盖启动后 26.33–160.09 秒（约 134 秒）。结果：

| 项目 | 实测结果 |
| --- | --- |
| USB 类型与状态 | 全程 online=1、PD |
| 输入限流 | 全程 3,000,000µA，没有变为零 |
| USB 实际输入电流 | 1.675–1.916A |
| USB 电压 | 4.627–4.686V |
| 电池净电流 | 全程正值，0.775–1.596A |
| 电池状态与电量 | 全程 Charging，98%→99% |
| charge counter | 4253→4291，与净充入方向一致，单位问题仍另行核对 |
| 剩余充电时间 | 1620→420 秒，没有异常的 3932100 秒 |
| USB 限制取电开关 | `restrict_chg=0` |

原始证据为本地 `first-pc-after-reboot-samples.jsonl`、`first-pc-after-reboot-dmesg.txt`、`first-pc-after-reboot-logcat.txt`，结构化结果为 `first-pc-after-reboot-summary.json`，终态及内核日志另存 `first-pc-after-reboot-end.txt`。所有记录均留在忽略目录，没有提交设备转储。

本次在尚未满电时验证了重启后的首次电脑连接，持续正常充电，未复现用户最初描述的故障。故“只要重启后第一次插电脑就不充电”不是当前证据支持的必现条件，也不能因此宣布已修复或否定此前历史故障。先前接过充电头的影响是否能跨暖重启保留仍未知。下一步应在再次出现非满电零输入时先保存连接状态与日志，再做同条件对照；当前不继续反复重启，也不强制限流或关闭温控。
