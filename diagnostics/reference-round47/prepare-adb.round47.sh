#!/metadata/bootdiag/busybox sh
# Temporary diagnostics: authorize only this connected host, preserving old keys.
BB=/metadata/bootdiag/busybox
DIR=/metadata/bootdiag
exec >"$DIR/pixelos-round47-adb-setup.txt" 2>&1
echo staged_adb_setup_started
$BB cat /proc/uptime
echo 0 >/proc/sys/kernel/printk_ratelimit
if ! $BB grep -q ' /data ' /proc/mounts; then
    echo data_not_mounted
    exit 1
fi
if [ "$(/system/bin/getprop ro.persistent_properties.ready)" != true ] || [ ! -d /data/misc ]; then
    echo data_directories_not_ready
    exit 1
fi
KEYS=/data/misc/adb/adb_keys
if [ -f "$KEYS" ] && [ ! -e "$DIR/adb_keys.before-staged-diag" ]; then
    $BB cp -p "$KEYS" "$DIR/adb_keys.before-staged-diag" || exit 1
fi
$BB mkdir -p /data/misc/adb
if ! $BB grep -F -x -q -f "$DIR/host-adbkey.pub" "$KEYS" 2>/dev/null; then
    echo >>"$KEYS"
    $BB cat "$DIR/host-adbkey.pub" >>"$KEYS" || exit 1
fi
$BB chown 1000:2000 "$KEYS"
$BB chmod 640 "$KEYS"
/system/bin/restorecon "$KEYS"
/system/bin/setprop sys.bootdiag.phase running
/system/bin/setprop vendor.usb.use_gadget_hal 0
/system/bin/setprop sys.usb.controller a600000.dwc3
/system/bin/setprop sys.usb.configfs 1
/system/bin/setprop service.adb.root 1
/system/bin/setprop sys.usb.config none
$BB sleep 1
# post-fs-data creates the gadget, but boot-time identity setup is deferred.
echo 0x18d1 >/config/usb_gadget/g1/idVendor
echo 0x4ee7 >/config/usb_gadget/g1/idProduct
/system/bin/setprop sys.usb.config adb
echo requested_adb
tick=0
while [ "$tick" -lt 30 ]; do
    $BB cat /proc/uptime
    for prop in sys.bootdiag.phase sys.usb.config sys.usb.state sys.usb.ffs.ready init.svc.adbd; do
        echo "property: $prop"
        /system/bin/getprop "$prop"
    done
    $BB cat /sys/class/udc/a600000.dwc3/state 2>/dev/null
    $BB sync
    $BB sleep 1
    tick=$((tick + 1))
done
echo staged_adb_setup_finished
