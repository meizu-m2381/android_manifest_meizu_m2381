#!/metadata/bootdiag/busybox sh
# Preserve only the exact directory contents created by the early diagnostic ADB script.
# A mismatch leaves the directory untouched; this never deletes userdata.
BB=${BOOTDIAG_BUSYBOX:-/metadata/bootdiag/busybox}
DIR=${BOOTDIAG_DIR:-/metadata/bootdiag}
MISC=${BOOTDIAG_MISC_DIR:-/data/misc}
ARCHIVE=${BOOTDIAG_MISC_ARCHIVE:-/data/misc.bootdiag-round39}
LOG=${BOOTDIAG_LOG:-/dev/kmsg}

report() { echo "<4>BOOTDIAG39: adb_parent_$1" >>"$LOG"; }

if [ ! -e "$MISC" ] && [ ! -L "$MISC" ]; then
    report absent
    exit 0
fi
if [ -L "$MISC" ] || [ ! -d "$MISC" ] || [ -L "$MISC/adb" ] ||
   [ ! -d "$MISC/adb" ] || [ -L "$MISC/adb/adb_keys" ] ||
   [ ! -f "$MISC/adb/adb_keys" ]; then
    report unexpected_type_untouched
    exit 0
fi
if [ "$("$BB" ls -A "$MISC")" != adb ] ||
   [ "$("$BB" ls -A "$MISC/adb")" != adb_keys ]; then
    report extra_contents_untouched
    exit 0
fi
if [ -e "$DIR/adb_keys.before-staged-diag" ] ||
   [ -L "$DIR/adb_keys.before-staged-diag" ] || [ ! -s "$DIR/host-adbkey.pub" ]; then
    report original_keys_or_missing_reference_untouched
    exit 0
fi
if [ -e "$ARCHIVE" ] || [ -L "$ARCHIVE" ] ||
   [ "$("$BB" dirname "$MISC")" != "$("$BB" dirname "$ARCHIVE")" ]; then
    report archive_not_available_untouched
    exit 0
fi
EXPECTED="$DIR/pixelos-round39-expected-adb-key"
if ! { echo; "$BB" cat "$DIR/host-adbkey.pub"; } >"$EXPECTED"; then
    report reference_failed_untouched
    exit 0
fi
if ! "$BB" cmp -s "$EXPECTED" "$MISC/adb/adb_keys"; then
    report key_mismatch_untouched
    exit 0
fi
"$BB" lsattr -d "$MISC" >"$DIR/pixelos-round39-misc-attributes.txt" 2>&1
if "$BB" mv -nT "$MISC" "$ARCHIVE"; then
    "$BB" sync
    if [ ! -e "$MISC" ] && [ -f "$ARCHIVE/adb/adb_keys" ] &&
       "$BB" cmp -s "$EXPECTED" "$ARCHIVE/adb/adb_keys"; then
        report archived_exact_diagnostic_contents
        exit 0
    fi
fi
report archive_failed_inspect_before_retry
exit 1
