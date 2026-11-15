#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
tick=0
while [ "$tick" -lt 180 ]; do
    data_mounted=0
    $BB grep -q ' /data ' /proc/mounts && data_mounted=1
    completed=$(/system/bin/getprop sys.boot_completed)
    echo "<4>BOOTDIAG47: runtime_tick=$tick data_mounted=$data_mounted boot_completed=$completed" >/dev/kmsg
    $BB sleep 1
    tick=$((tick + 1))
done
