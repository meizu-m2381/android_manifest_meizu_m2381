#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
OUT=/metadata/bootdiag/pixelos-round47-runtime.txt
[ -L "$OUT" ] && exit 2
exec >>"$OUT" 2>&1
echo runtime_start
$BB cat /proc/sys/kernel/random/boot_id
tick=0
while [ "$tick" -lt 180 ]; do
    echo "runtime_tick=$tick"
    $BB cat /proc/uptime
    echo "boot_completed=$(/system/bin/getprop sys.boot_completed)"
    echo "zygote=$(/system/bin/getprop init.svc.zygote)"
    echo "surfaceflinger=$(/system/bin/getprop init.svc.surfaceflinger)"
    echo "adbd=$(/system/bin/getprop init.svc.adbd)"
    echo "usb=$(/system/bin/getprop sys.usb.state)"
    echo "system_server_pid=$(/system/bin/pidof system_server)"
    echo "surfaceflinger_pid=$(/system/bin/pidof surfaceflinger)"
    $BB sync
    $BB sleep 5
    tick=$((tick + 5))
done
