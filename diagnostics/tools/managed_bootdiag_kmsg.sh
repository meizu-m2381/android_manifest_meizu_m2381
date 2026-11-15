#!/metadata/bootdiag/busybox sh
# BusyBox ash measures this limit in 512-byte units: stop at 4 MiB.
ulimit -f 8192
exec /metadata/bootdiag/kmsg /metadata/bootdiag/pixelos-round10-kmsg.log
