#!/usr/bin/env bash
# 生成第二十三组 vendor 批量驱动加载隔离候选，不操作设备。
set -euo pipefail
if [[ ${M2381_ENABLE_HISTORICAL_DIAGNOSTICS:-} != 1 ]]; then
    echo 'Historical workflow only; read diagnostics/README.md and supply archived inputs first.' >&2
    exit 2
fi
repo_dir=$(cd "$(dirname "$0")/.." && pwd)
aosp_dir=${1:?用法: build-vendor-loader-isolation-diag.sh AOSP目录 前组镜像目录 新镜像目录}
previous_images=${2:?缺少前组镜像目录}
candidate_dir=${3:?缺少新镜像目录}
diagnostics_dir=$repo_dir/logs/boot-audit-20261112/round23
python3 "$repo_dir/tools/prepare_vendor_loader_isolation_diag.py" \
    --previous "$repo_dir/logs/boot-audit-20261112/round22" --output "$diagnostics_dir"
for rc_file in "$diagnostics_dir"/*.rc; do
    "$aosp_dir/out/host/linux-x86/bin/host_init_verifier" "$rc_file"
done
for shell_file in "$diagnostics_dir"/*.sh; do
    bash -n "$shell_file"
done
python3 "$repo_dir/tools/prepare_boot_candidate.py" --aosp "$aosp_dir" \
    --previous "$previous_images" --output "$candidate_dir" --round 23 \
    --first-stage-script "$repo_dir/tools/first_stage_managed_diag.sh" \
    --init-rc /metadata/bootdiag/init.round23.rc --reuse-previous-images \
    > "$diagnostics_dir/build.log" 2>&1
cat "$candidate_dir/verify-avb.log"
