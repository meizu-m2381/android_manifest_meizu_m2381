> 历史核查记录（已去除启动标识）。以 当前状态（原工作区：`../status.md`） 为准；文中日志和截图留在原本地工作区，未随本仓库发布。不是刷机指南。

# 魅族 20 原生 OpenGL 修复（2026-11-14）

用户反馈 Chrome 一打开就闪退，随后明确要求修复原生 OpenGL。设备沿用第四十七组启动链及已验证的 Wi-Fi、蓝牙、震动配置，未清除 Chrome 数据。

## 原因与隔离验证

Chrome 157.0.8103.50 的日志显示：`eglCreateContext ES 3.0 failed with error EGL_BAD_ATTRIBUTE`，GPU 子进程退出，最后主进程因 `GPU process isn't usable. Goodbye.` 主动 abort。系统 HWUI、SurfaceFlinger 使用 Vulkan，所以桌面正常不能证明 GLES 正常。

先给 Chrome 单独选择系统 ANGLE，确认 ANGLE 使用 Adreno 740 Vulkan，Chrome 可以启动。这是排查用的临时替代路径，用户要求修复原生 GL 后已删除两项 `angle_gl_driver_selection_*` 设置；没有改为全局 ANGLE。

独立 EGL 探针请求 ES 2.0、3.0、3.1、3.2，虽然上下文创建与 makeCurrent 返回成功，GL 却报告拼写错误的 `Qualcomm Technolgies / Adreno (TM) 4XX / OpenGL ES 3.0`，清屏读回恒为全零而不是预期颜色。单独改变 `debug.egl.hw` 为 1 没有改善，已恢复为原值 0，不能将该属性当作根因。

系统调用追踪确认 `/dev/kgsl-3d0` 可打开，主要设备初始化 ioctl 成功；加载器同时打开 `/vendor/lib64/libGLESv2_adreno.so` 和 `/vendor/lib64/egl/libGLESv2_adreno.so`。两者字节相同但 inode 不同。Zygote 的实际映射也同时存在这两套 GLES 库，因此应用继承了分裂的驱动全局/TLS 状态：EGL 上下文与 GL 调用使用了不同实例。

仅临时把根目录驱动 bind 到 `egl/` 对应路径，使加载器识别为同一底层文件，就恢复了 `Qualcomm / Adreno (TM) 740 / OpenGL ES 3.2 V@0676.32`。arm64 和 arm 的四组上下文分别均成功，清屏后实际读回 `64,128,191,255`、GL 错误为 0。该对比没有修改驱动代码。

Zygote 已预加载旧实例，临时 bind 后重新启动 Chrome 仍继承旧映射，不能用“进程启动命令成功”冒充 Chrome 已修好；最终应用验证须在持久镜像冷启动后完成。

## 持久修改与构建验证

- 保留 `vendor/lib*/egl/` 的原驱动，将根目录 `libEGL_adreno.so`、`libGLESv2_adreno.so` 四个独立副本改为相对链接 `egl/<同名文件>`，覆盖 arm/arm64。
- `device/meizu/m2381/Android.bp` 维护四个 `install_symlink`，产品显式选择；移除对应旧预编译安装规则，加入 blob 排除列表，避免下一次提取覆盖链接。
- `tools/configure_adreno_symlinks.py` 先确认现存副本与标准文件摘要相同，再复用安装规则清理函数；重复执行不再修改文件。构建脚本同步后调用。
- 增加 `tools/egl_probe.c` 与 `tools/build_egl_probe.py`：用现有 AOSP bionic/clang 编译两种 ABI 的独立探针，核对实际像素而非只核对返回码；未加入系统产品包。

vendorimage 构建成功（5 分 16 秒）。对实际 EROFS 逐文件比较已安装网络修正版，仅上述四个路径从文件变为相对符号链接，目标驱动字节保持；Wi-Fi、蓝牙、震动、Vulkan 和其他镜像文件保持。完整 AVB 链和主机六份待刷文件摘要通过。Python、shell 语法、安装路径冲突检查通过。保留已验证启动链，不在本轮切换全局 HWUI/SurfaceFlinger 后端。

## 实机持久验证

修正版已刷入，实际六个分区 SHA-256 与待刷镜像全部一致。启动后四个根目录路径均为预期相对链接，没有临时 Adreno bind mount；Zygote 仅映射 `egl/` 中的一套 EGL/GLES 驱动。BCB 命令已清空，其余 2016 字节保持。

首次启动 ID 为 `[boot-id omitted]`。随后执行一次普通 `adb reboot`，21.6 秒内 `sys.boot_completed=1`，新启动 ID 为 `[boot-id omitted]`。两次启动后分别验证：

- arm64、arm 探针的 ES 2.0、3.0、3.1、3.2 均为 `PASS_COUNT=4/4`，实际清屏像素 `64,128,191,255`，GL 错误为 0。
- Chrome WebGL 和 WebGL2 均成功创建上下文、编译着色器、链接程序并绘制三角形；实际三角形像素 `255,0,0,255`，两项均 `pass=true`。
- Chrome 报告 `ANGLE (Qualcomm, Adreno (TM) 740, OpenGL ES 3.2)`，GPU 进程实际映射原生 Adreno EGL/GLES。这里的 ANGLE 是 Chromium 自身的图形层，后端为原生 OpenGL；系统的两项逐应用 ANGLE 设置均为 `null`，未依赖先前的 Vulkan 替代设置。
- 本次重启日志没有重现 Chrome 的 `EGL_BAD_ATTRIBUTE` 或 `GPU process isn't usable`。屏幕截图确认 Chrome 测试页及两个红色绘制区域正常显示。

回归检查中 Wi-Fi 自动连回原网络，蓝牙状态为 ON，`vendor.ssgtzd` 与震动服务运行。此次没有重新验证蓝牙文件传输或震动力度；Wi-Fi 仍报告此前已有的 `PARTIAL_CONNECTIVITY`，不据此宣称外网全面可用。系统 HWUI 仍为 `skiavk`，SurfaceFlinger 仍为 `skiavkthreaded`。本轮验证覆盖上下文、像素和简单着色器及一次普通重启，尚未覆盖所有应用、游戏或长时间稳定性。

证据保存在忽略目录 `logs/chrome-audit-20261114/`，包括 `normal-reboot.json`、`probe-postreboot-{arm64,arm}.txt`、`chrome-render-{postflash,postreboot}.json`、GPU 映射、日志与截图；不提交设备转储、网页私有数据或镜像。
