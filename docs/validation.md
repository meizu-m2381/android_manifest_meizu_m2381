# 维护检查

以下命令在 Linux/WSL 中执行；`port_root` 指本工具仓，`android_root` 指已同步
设备、vendor、内核和上游依赖的 Android 源码根目录。检查不会刷写手机。

```bash
port_root=/path/to/android_manifest_meizu_m2381
android_root=/path/to/android
python3 "$port_root/tools/check_bundled_inputs.py" --root "$android_root"
python3 "$port_root/tools/check_local_inputs.py" --root "$android_root"
python3 "$port_root/tools/check_source_lfs.py" --root "$android_root"
python3 "$port_root/tools/configure_pd_icl.py" --root "$android_root"
python3 "$android_root/device/meizu/m2381/tools/configure_blob_compat.py" --aosp "$android_root"
python3 "$port_root/tools/apply_platform_patches.py" --aosp "$android_root" --require-unpatched
M2381_AOSP_ROOT="$android_root" python3 -m unittest discover -s "$port_root/tools/tests" -v
```

迁移测试使用临时目录，检查恢复幂等性、未知输入/冲突保护、硬链接隔离及真实
blob/helper 复现。未设置 `M2381_AOSP_ROOT` 会跳过真实 ELF 用例，不能将此称为
完整通过。实际修补需上游提供的匹配 patchelf 与冻结 API33 输入。

修改服务或资源后应实际构建相应目标，核对安装清单和最终镜像内文件，避免只测
暂存目录。DT_NEEDED 符号集合及 `linker --list` 不能代替完整重定位、dlopen、
服务启动和硬件检查。功能验证现状与未完成的场景见 [功能状态](status.md)。
