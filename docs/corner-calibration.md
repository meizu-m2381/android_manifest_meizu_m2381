# 屏幕与应用开合圆角校准（2026-11-16）

设备 overlay 原先使用原厂覆盖包的 `20dp`，在当前 450dpi 下约为 56px。
用户实机观察应用开合动画比实体屏幕更方，因此原厂资源数值不能直接视为
当前 AOSP 显示栈下已校准的面板几何。

应用全屏过渡经 `QuickStepContract.getWindowCornerRadius` 读取框架圆角。
真机 Pixel Launcher 资源查询与框架一致，没有发现独立的设备窗口圆角覆盖。
设备树的 `FrameworkOverlayM2381/res/values/dimens.xml` 将
`rounded_corner_radius` 设置为 `94px`；顶部和底部保持 0，沿用公共半径。
使用物理像素，避免半径随用户显示大小设置变化。不修改 AOSP 或桌面源码。

先通过完整设备 overlay 的校准副本设置 100px，用户反馈需稍尖；调整为
94px 后正常重启，框架和桌面查询均返回 `94.0px`，用户确认基本贴合。
这是目视校准，不是面板边缘的精密测量，也不要求动画缩放全程维持固定半径。

当前手机仍通过 metadata 诊断入口早期挂载校准 overlay，原 product APK
没有改写。完整备份、候选 APK 和启动配置在私有 `.local-flash/corners-20261116/`。
正式镜像安装包含 94px 的设备 overlay 后，应撤销该临时挂载，避免覆盖新包。
本轮校准 APK 已通过 aapt2 编译、链接和签名检查；没有全量构建或刷写 ROM。
指纹原厂坐标和 deep 待机选择在校准后重启仍保留。
