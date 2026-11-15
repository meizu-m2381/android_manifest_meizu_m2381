#!/bootdiag/busybox sh
# Second-stage init owns the collectors; first stage only marks the hook.
BB=/bootdiag/busybox
# libbase caches its /dev/kmsg fd. Set the mode before second-stage init opens it.
if [ -w /proc/sys/kernel/printk_devkmsg ]; then
    echo on >/proc/sys/kernel/printk_devkmsg
fi
if $BB grep -q ' /metadata ' /proc/mounts; then
    $BB mkdir -p /metadata/bootdiag
    echo hook_returning > /metadata/bootdiag/pixelos-round4-status.txt
    $BB sync
fi
exit 0
