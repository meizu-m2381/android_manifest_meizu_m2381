#!/metadata/bootdiag/busybox sh
BB=/metadata/bootdiag/busybox
DIR=/metadata/bootdiag
OUT=$DIR/pixelos-round10-tombstones
$BB mkdir -p "$OUT"
exec >"$DIR/pixelos-round10-watch.txt" 2>&1
echo managed_collector_started
tick=0
while [ "$tick" -lt 120 ]; do
    echo "=== heartbeat $tick ==="
    $BB cat /proc/uptime /sys/fs/selinux/enforce
    # Capture status without enumerating every process's procfs files.
    if [ "$((tick % 4))" -eq 0 ]; then
        $BB ps -o pid,ppid,comm
        for prop in init.svc.bootdiag_logcat init.svc.bootdiag_kmsg init.svc.zygote init.svc.surfaceflinger init.svc.vendor.qti.hardware.display.composer sys.boot_completed sys.powerctl; do
            echo "property: $prop"
            /system/bin/getprop "$prop"
        done
        $BB df -k /metadata /data
    fi
    count=0
    for file in /data/tombstones/tombstone_*; do
        case "$file" in *.pb|*.tmp) continue ;; esac
        [ -f "$file" ] || continue
        count=$((count + 1))
        [ "$count" -gt 32 ] && break
        name=${file##*/}
        size=$($BB stat -c %s "$file")
        [ "$size" -gt 65536 ] && size=65536
        saved=$($BB stat -c %s "$OUT/$name" 2>/dev/null)
        [ "$saved" = "$size" ] && continue
        echo "copying $name"
        $BB head -c 65536 "$file" > "$OUT/$name.tmp"
        $BB mv "$OUT/$name.tmp" "$OUT/$name"
    done
    $BB sync
    $BB sleep 0.5
    tick=$((tick + 1))
done
echo managed_collector_finished
$BB sync
