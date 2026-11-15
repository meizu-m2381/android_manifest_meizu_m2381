> 历史核查记录（已去除启动标识）。以 当前状态（原工作区：`../status.md`） 为准；文中日志和截图留在原本地工作区，未随本仓库发布。不是刷机指南。

# 撤回 OpenGL 绕过配置与实机验证（2026-11-14）

用户要求撤回之前因 OpenGL 不可用而增加的配置，并验证功能。

## 修改与部署

从设备树 `configs/properties/system.prop` 删除三项设置及过时注释，并在确认 WSL 源文件与修改前 Git 内容一致后同步该文件：

- `debug.hwui.renderer=skiavk`
- `debug.renderengine.backend=skiavkthreaded`
- `service.sf.prime_shader_cache=false`

实机读取确认当前已安装的 system/product/vendor 等属性文件没有这三项，实际来自 `/metadata/bootdiag/init.round47.rc`。同一路径的 early-init 中按阶段删去对应三行，保留其他行逐字节不变，没有改成强制 `skiagl` 或强制预热的替代开关。最终三项 `getprop` 均为空，框架使用自身默认值。

三份候选 init 都通过 `host_init_verifier`。每阶段先停止诊断日志写入，将七份旧日志拉取并逐项核对主机/设备 SHA-256 后删除原日志，使 metadata 可用空间恢复到至少 8 MiB；随后原子替换 init，保持 root:root、0644、metadata_file 标签，核对字节及摘要再正常重启。启动前确认 BCB 命令为空。

本轮没有刷写分区或重编整包，设备实际镜像不含待删除属性，故无需通过重刷应用此变更。保留 Adreno 单实例链接、EGL/Vulkan mapper ABI 修补及此前网络、震动、颜色模式修复。

最终 init SHA-256：`5d9bed4d08287e24a92af8497046209139fc5e6593f342862b2c5520ae2c7681`。

## 分阶段验证

| 阶段 | 已撤回的设置 | 正常启动耗时 | 启动 ID |
| --- | --- | --- | --- |
| 应用恢复默认 | HWUI Vulkan 强制项 | 18.8 秒 | `[boot-id omitted]` |
| 合成恢复默认 | 再删除 RenderEngine Vulkan 强制项 | 18.8 秒 | `[boot-id omitted]` |
| 全部恢复默认 | 再删除关闭预热的设置 | 19.0 秒 | `[boot-id omitted]` |

前两阶段分别验证颜色页三项名称与切换、彩色预览、OpenGL 管线与核心进程状态。第一阶段至少运行到 141 秒，SurfaceFlinger/system_server PID 保持 1712/2732；第二阶段至少到 226 秒，PID 保持 1710/2677。

最终默认配置下：

- SurfaceFlinger 报告 `Qualcomm / Adreno (TM) 740 / OpenGL ES 3.2 V@0676.32`。SystemUI、桌面、设置的 gfxinfo 都是 `Pipeline=Skia (OpenGL)`，分别已绘制 1468、505、501 帧；帧数仅用于证明实际绘制，不是性能基准。
- 首次 ADB 即保存的日志显示 `Shader cache generated 140 shaders in 2217.642578 ms`，证明启动预热实际执行；所核对日志没有重现原来的纹理断言、Chrome EGL_BAD_ATTRIBUTE 或 GPU process 不可用错误。
- arm64 和 arm 独立 EGL/GLES 探针均为 `PASS_COUNT=4/4`，覆盖 ES 2.0、3.0、3.1、3.2 的上下文和真实像素。
- Chrome WebGL、WebGL2 的上下文、着色器编译、程序链接及三角形绘制均通过；清屏像素为 `64,128,191,255`、三角形像素为 `255,0,0,255`、GL 错误为 0。后端为 Adreno 原生 OpenGL，未启用系统逐应用 ANGLE 替代路径。
- 颜色页三个选项“自然色、增强色、饱和色”均正确写入 0、1、2；彩色预览正常，阅读模式始终关闭。最终恢复自然色。
- 展开/收起快捷设置、返回桌面、息屏进入 Dozing、唤醒回到 Awake 后重新打开颜色页均通过，截图正常。用户确认“画面和彩色正常，触摸正常”。
- 最终观察到 uptime 411 秒时，SurfaceFlinger/system_server PID 仍为本次启动的 1664/2662，`sys.boot_completed=1`，诊断自动返回计时服务已停止。
- Wi-Fi 自动连接，蓝牙为 ON，震动服务和 vendor.ssgtzd 为 running；这些属于状态回归，没有重新测试蓝牙传输、震动力度或外网连通性。

已有 vendor.dpmd ABI 缺符号等其他服务错误仍存在，不能把本轮图形测试通过解释为所有硬件功能均已修好。本轮未测试长时间游戏、全部应用或长期功耗稳定性。

证据保存在忽略目录 `logs/graphics-defaults-20261114/`：三个阶段的 init、启动记录和归档摘要，最终阶段的 shader 预热日志、两架构探针、Chrome 绘制结果、颜色页切换结果、gfxinfo、SurfaceFlinger 状态与截图。不提交镜像、设备转储或临时测试脚本。
