#!/usr/bin/env bash
# Run only after the preparation in docs/build.md. No device operations.
set -eo pipefail
aosp_dir=$(realpath "${1:?Usage: build-pixelos.sh AOSP_ROOT [JOBS]}")
jobs=${2:-$(nproc)}
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be positive' >&2; exit 2; }
python3 "$repo_dir/tools/configure_pd_icl.py" --root "$aosp_dir"
python3 "$repo_dir/tools/check_local_inputs.py" --root "$aosp_dir"
python3 "$repo_dir/tools/check_source_lfs.py" --root "$aosp_dir"
python3 "$repo_dir/tools/apply_platform_patches.py" --aosp "$aosp_dir" --require-applied
cd "$aosp_dir"
source build/envsetup.sh
target_release=$(sed -n 's/^aosp_target_release=//p' vendor/lineage/vars/aosp_target_release)
[[ "$target_release" =~ ^[a-z0-9_]+$ ]] || { echo 'Missing or invalid target release' >&2; exit 2; }
lunch "custom_m2381-$target_release-userdebug"
[[ "$(get_build_var TARGET_DEVICE)" == m2381 && "$(get_build_var TARGET_ARCH)" == arm64 ]] || {
    echo 'Product configuration did not select the M2381 ARM64 board' >&2
    exit 2
}
m pixelos -j"$jobs"
