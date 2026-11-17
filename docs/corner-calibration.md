# 屏幕与窗口圆角

设备 `FrameworkOverlayM2381/res/values/dimens.xml` 将 `rounded_corner_radius`
设置为 `94px`，顶部/底部保持 0，沿用公共半径。使用物理像素，避免随显示大小
设置变化；不修改 AOSP 或桌面源码。

应用过渡通过 `QuickStepContract.getWindowCornerRadius` 使用框架资源；
Pixel Launcher 与框架查询均返回 94px，用户确认基本贴合实体屏幕。
这是目视校准，不是面板边缘的精密测量。原厂 20dp 在当前显示栈下未达到相同效果。

旧安装若使用 metadata 临时挂载 overlay，安装包含正式 RRO 的镜像后需撤销
该挂载，避免旧 APK 覆盖后续配置。
