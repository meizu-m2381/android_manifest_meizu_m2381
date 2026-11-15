> 历史核查记录（已去除启动标识）。以 当前状态（原工作区：`../status.md`） 为准；文中日志和截图留在原本地工作区，未随本仓库发布。不是刷机指南。

# 魅族 20 屏幕几何与辅助相机适配（2026-11-14）

## 原厂资源与屏幕修正

原设备树沿用了 m2468 的屏幕几何。本轮以魅族 20 官方 Flyme 12.6.0.0A 的 `framework-res.apk`、本机保留的原厂 vendor 覆盖包与 system_ext SystemUI 为依据。`backup/super/super.img` 的 system 已是 LineageOS GSI，不能将其中的 framework-res 当成 Flyme 原厂参数。

官方固件来自魅族 20 下载页 `https://foru.flyme.cn/firmwarelist-195.html`。通过 HTTP Range 读取 ZIP / payload 元数据，并按需还原 framework-res 所在的 EROFS 数据块；每个下载的 InstallOperation 校验 SHA-256。没有下载整个 6.66 GB 固件，未执行整包 MD5 校验。原厂文件摘要：

| 文件 | SHA-256 |
| --- | --- |
| 官方 framework-res.apk | `b166f5f675075467a5f1aeeff4d4b4c7c0b5a9d1fd8f008dfd2c4c897db915de` |
| FrameworksResTarget_Vendor.apk | `0f5ce1541f53a9d6b1f5d584c372316f536135f7ea96f8e0352194817459b8e8` |
| 本机原厂 SystemUI.apk | `60ed4b5e2e60e8e019d0a2b0b35ba2d2293cf1ee02973098bfcd8d286e891e9c` |

| 参数 | 旧设备树 | 原厂资源 / 新配置 |
| --- | --- | --- |
| 挖孔圆心 | 屏幕中线，y=76 px | 屏幕中线，y=63.01 px |
| 挖孔半径 | 16 px | 30.73 px |
| 避让矩形 | 62×145 px，向右偏移 31 px | 62×116 px，按实际挖孔居中 |
| 状态栏默认 / 竖屏 | 145 px | 116 px |
| 状态栏横屏 | 继承竖屏 145 px | 原厂同样继承竖屏，显式配置 116 px |
| 圆角半径 | 63 px | 原厂 vendor 覆盖包的 20 dp |
| 圆角内容额外留白 | 0 dp | 0 dp |
| SystemUI 状态栏左右留白 | 左 20 dp、右 0 dp | 有效两侧约 20 dp；AOSP 右侧已含隐私点预留，内层仍为 0 dp |
| 状态栏顶部留白 | 框架默认 | 原厂 SystemUI 的 10 px |
| pixel_pitch | 54.44 | 原厂 SystemUI 覆盖包的 50 |

Flyme framework 的通用圆角值是 36 dp，但本机原厂 `FrameworksResTarget_Vendor.apk` 会将其覆盖为 20 dp，不能只取 framework 默认值。当前原生分辨率为 1080×2400，密度 450 dpi。

挖孔路径逐字采用原厂圆形路径。原厂近似矩形路径从 x=0 向右画 62 px；AOSP 以屏幕中线为坐标原点，照抄会让避让区域右偏。新配置保留原厂宽高，将起点改为 x=-31，使矩形覆盖实际挖孔。这是对 AOSP 坐标语义的适配，不声称矩形路径与原厂字符串逐字相同。

Flyme 的 SystemUI 左右 padding 均为 20 dp，但 AOSP 的 `StatusBarContentInsetsProvider` 另按 `ongoing_appops_dot_min_padding=20dp` 在尾端预留隐私点空间，`PhoneStatusBarView` 再应用内层 `status_bar_padding_end`。首次直接复制原厂右侧 20 dp 后，外层 56 px 与内层 56 px 叠加，用户指出右侧明显宽于左侧。最终将内层右侧恢复 0 dp，保留 AOSP 隐私指示点，不改圆角、挖孔及左侧留白；目标是匹配原厂有效间距，而非将 Flyme 的布局数值重复套用。

## 后置镜头缺失

修复前 Camera Provider 只上报 ID 0、1。内核日志却显示四个实际传感器均探测成功：主摄 s5kgn5sp、前摄 s5kgd2sp03、景深 s5k5e9yx04、超广角 s5k3p9sx；枚举时其他候选型号 probe failed 不代表实际镜头坏了。

反汇编和 QTI 源码共同表明，CamX 的 `GetDevicesSettings()` 会通过 `isRunningWithVendorEnhancedFramework()` 选择相机配置。缺少 `ro.vendor.qti.va_aosp.support` 时走 kailua GSI 的双摄配置；设置为 1 后恢复五个 HAL 设备：

| ID | 类型 | 普通 JPEG 实测尺寸 |
| --- | --- | --- |
| 0 | 后置主摄 | 4080×3060 |
| 1 | 前摄 | 3264×2448 |
| 2 | 后置景深传感器 | 不作为日常拍照镜头开放 |
| 3 | 后置超广角 | 4640×3480 |
| 4 | 组合 3 / 0 / 2 的逻辑摄像头 | 不重复添加到镜头选择器 |

`Number of normal camera devices: 2` 是 API1 列表的数量，不能据此否定 Camera2 已可访问其他镜头。新建 `ApertureOverlayM2381`，启用辅助镜头选择并忽略 ID 2、4。测试时多出的 `1.1×` 来自辅助景深传感器的视角换算；日常界面仅保留主摄与 `.7×` 超广角，前摄使用翻转按钮。

排查时还临时设置过 `ro.vendor.camera.no_vts=1`。该设置单独不恢复镜头，不写入设备树或启动脚本；重启后应消失。

## 拍照超时与 Ultra HDR

修复镜头枚举后，Aperture 默认选择框架合成的 JPEG Ultra HDR，产生 P010（0x36）与 JPEG 两路输出。主摄拍照未保存文件，随后 CamX 请求线程超时并由 `Usecase::DumpSystemEvent()` 触发 provider 重启；此前双摄配置下也已有同类超时。

使用 Android 已有的 `ro.camera.disableJpegR=1` 禁止框架派生 JPEG/R 能力后，Aperture 保持用户原来的 Ultra HDR 偏好值，但根据实际能力回退到普通 JPEG。主摄、超广角和前摄各保存一张有效 JPEG，输出流各完成一帧，拍照后预览继续。没有修改用户偏好文件或清除应用数据。本轮保留普通 JPEG，不宣称 Ultra HDR 合成已修复。

两项属性放在设备 product.prop 中，和产品框架适配一同加载；本轮不替换相机厂商二进制。

## 镜像构建与检查

三个 RRO 从设备树 XML 使用本树 AAPT2、signapk 和原签名证书编译签名；现有 FrameworkOverlay 的证书 SHA-256 与新包一致。首次 Soong 模块构建在 bootstrap / globs 阶段中断，未将其报告为完整构建成功。

首轮手工打包遗漏 `<application android:hasCode="false" />`，PackageManager 在启动扫描时拒绝三个 RRO。用户观察到状态栏偏上、时间靠边；实际 SystemUI 左右 padding 为 4 dp、顶部 0 dp，未取得预期 20 dp / 10 px。资源查询本身不足以证明覆盖包已被完整加载。本轮补齐三个 Manifest 的无代码声明，重新编译、生成镜像并刷入；后续以包安装日志、三个 `[x]` 启用状态、资源值及实际位置共同验收。

基于上一版已验证 product 文件树制作候选，实际内容仅改变 `etc/build.prop`、两个屏幕 RRO，并新增相机 RRO。EROFS 完整性检查通过；原有 558 个路径的 UID/GID、权限、xattr 大小均一致，新 RRO 为 root:root、0644 且带 SELinux 标签。只有 product 与 vbmeta_system 摘要改变，完整 AVB 链验证通过。

构建期间主机空间不足产生过不完整 EROFS，完整性 / AVB 检查将其拦截，没有刷入。对 SHA-256 完全相同的历史镜像建立硬链接，保留原路径与字节，恢复空间后重新构建并重新检查。临时解包的 system / system_ext 镜像已删除，原始备份保留。

证据与脚本位于忽略目录 `logs/stock-screen-camera-20261114/`。截图、照片、设备日志及镜像不提交 Git。

## 最终刷入与实机验收

加载三个覆盖包后的第一版启动 ID 为 `[boot-id omitted]`，下列相机与 OpenGL 测试在该启动上执行；随后仅修正 SystemUI 右侧重复留白并再次刷入。最终启动 ID 为 `[boot-id omitted]`，直接读取 b 槽 boot、init_boot、vendor_boot、vbmeta_system、vbmeta、vendor、product 七个分区的 SHA-256，全部与最终候选清单匹配，结果保存在 `flashed-partition-verification-v4.json`。最终 product 摘要为 `e5382ce0e7f132b89b066c1fb0a22ff69930b82ad6a57cd57054a9db576d9650`，vbmeta_system 为 `2ebff5105b60f147650b6048f7b82c644ae1cecb194a0eac15d36ae5ce1d37d6`。

- 三个 RRO 均已安装且显示 `[x]`；两项相机属性重启后均为 1，临时 `ro.vendor.camera.no_vts` 为空。
- 竖屏实际挖孔避让区域为 `Rect(509,0 - 571,116)`，四角半径 56 px。最终 SystemUI 实际资源为左侧 20 dp、内层右侧 0 dp、顶部 10 px；右侧外层保留 56 px 隐私点安全空间，`StatusBarInsetsProvider` 边界为 `Rect(0,0 - 1024,116)`。已对最终启动再次核对三个覆盖包、相机属性及旧绕过属性状态，并检查解锁后截图的实际左右间距。
- 解锁后进入设置，确认真实旋转为 `ROTATION_90`、画面为 2400×1080。挖孔避让区域转到左侧 `Rect(0,509 - 116,571)`，四角半径保持 56 px，状态栏高 116 px。测试后恢复原来的竖屏锁定。
- 后置相机 UI 仅显示 `.7`、`1×`，不再显示景深档位 `1.1×`。首次打开只有一个档位是应用记住了前摄选择，切回后置并重新打开后确认两档。
- 最终启动上的主摄、超广角、前摄依次拍照，分别保存 4080×3060、4640×3480、3264×2448 的 JPEG；Pillow 完整解码及 JPEG 结束标志检查通过，活动 Camera ID 分别为 0、3、1。三次拍照前后 provider PID 均为 12411。结果和摘要见 `final-jpeg-results.json`。
- 初次打开前摄并抓取诊断信息时，曾发生 provider 退出，应用收到错误 3，随后保留错误 8 并退出。重新启动应用后上述三摄拍照通过；再进行 45 秒前摄持续预览，provider PID 仍为 12411，活动 Camera ID 仍为 1。该次异常原因尚未确定，不能据短期复测声称相机长期稳定性已完全验证。
- arm / arm64 的原生 EGL 探针各测试 ES 2.0、3.0、3.1、3.2，均为 `PASS_COUNT=4/4`，读回颜色正确、`glerr=0`。三个旧 Vulkan 绕过属性仍为空；当前诊断 init 的 SHA-256 保持 `5d9bed4d08287e24a92af8497046209139fc5e6593f342862b2c5520ae2c7681`。

## 圆角与挖孔预览

使用解锁后的真实桌面截图（1080×2400），以 Pillow 叠加 R56 px 圆角、圆心 (540,63.01) / 半径 30.73 px 挖孔，4 倍抗锯齿生成：

- `output/screen-camera-20261114/screen-rounded-cutout.png`：整屏预览。
- `output/screen-camera-20261114/statusbar-geometry-check.png`：顶部原尺寸及几何标线对照。
- `output/screen-camera-20261114/statusbar-spacing-comparison.png`：右侧重复留白修正前后的实机截图对比。
- `output/screen-camera-20261114/geometry.json`：绘制参数；脚本为 `logs/stock-screen-camera-20261114/render-screen.py`。

已目视检查渲染结果，时间、通知及系统图标不与圆角、挖孔重叠。图片的遮罩是依据配置生成的模拟，不能证明配置与实体面板完全贴合；真实边缘及用户对状态栏间距的感受仍需真机确认。Ultra HDR 本轮仍回退普通 JPEG。
