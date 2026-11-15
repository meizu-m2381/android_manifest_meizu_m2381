#!/bootdiag/busybox sh
BB=/bootdiag/busybox
echo on > /proc/sys/kernel/printk_devkmsg
if ! $BB grep -q ' /metadata ' /proc/mounts; then
    echo 'BOOTDIAG: metadata is not mounted' > /dev/kmsg
    exit 1
fi
DIR=/metadata/bootdiag
$BB mkdir -p "$DIR"
echo hook_started > "$DIR/pixelos-round4-status.txt"
$BB setsid /bootdiag/kmsg "$DIR/pixelos-round4-kmsg.log" </dev/null >/dev/kmsg 2>&1 &
echo $! > "$DIR/pixelos-round4-logger.pid"
(
    exec 3</bootdiag/busybox
    exec 5>>"$DIR/pixelos-round4-logcat.txt"
    cd /proc || exit 1
    bb() { (exec -a busybox self/fd/3 "$@"); }
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        bb sleep 1
        if [ -e 1/root/system/bin/logcat ]; then
            # Start after switch_root, retain the metadata FD, bound disk usage.
            # Keep kernel/audit echo traffic from consuming the crash budget.
            bb chroot 1/root /system/bin/logcat -b main -b system -b crash \
                -v threadtime 'auditd:S' 'logd:S' 'first_stage.sh:S' '3:S' '*:V' 2>&1 |
                bb head -c 4194304 >&5
            break
        fi
    done
) </dev/null >/dev/null 2>&1 &
(
    # Keep the executable, output and procfs open across init's root/mount move.
    # Do not use absolute /proc paths or reopen /metadata after switch_root.
    exec 3</bootdiag/busybox
    exec 4>>"$DIR/pixelos-round4-processes.txt"
    cd /proc || exit 1
    bb() { (exec -a busybox self/fd/3 "$@"); }
    for delay in 2 5 15 30; do
        bb sleep "$delay"
        {
            echo "=== snapshot after sleep $delay ==="
            bb cat uptime
            echo '=== PID 1 ==='
            bb cat 1/status 1/wchan 1/stack
            bb readlink 1/exe
            bb readlink 1/root
            if [ "$delay" = 2 ]; then
                echo '=== linker configuration ==='
                bb cat 1/root/linkerconfig/ld.config.txt
            fi
            echo '=== mount table ==='
            bb cat 1/mounts
            # Scanning every PID generated thousands of permissive audit
            # records and crowded the logcat buffer before crash_dump ran.
            echo '=== collector state ==='
            bb cat self/status self/cgroup
        } >&4 2>&1
        bb sync
    done
) </dev/null >/dev/null 2>&1 &
(
    exec 3</bootdiag/busybox
    exec 6>>"$DIR/pixelos-round4-tombstones.txt"
    cd /proc || exit 1
    bb() { (exec -a busybox self/fd/3 "$@"); }
    for delay in 3 5 10 20; do
        bb sleep "$delay"
        {
            echo "=== native tombstones after sleep $delay ==="
            bb cat uptime
            for tombstone in 1/root/data/tombstones/tombstone_*; do
                case "$tombstone" in *.pb|*.tmp) continue ;; esac
                [ -f "$tombstone" ] || continue
                echo "=== $tombstone ==="
                bb head -c 65536 "$tombstone"
            done
        } >&6 2>&1
        bb sync
    done
) </dev/null >/dev/null 2>&1 &
echo hook_returning > "$DIR/pixelos-round4-status.txt"
echo 'BOOTDIAG: hook returning to init' > /dev/kmsg
exit 0
