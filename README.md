# android_manifest_meizu_m2381

Repository manifests, device compatibility and tooling for building the Meizu 20
(`m2381`) tree.

## Repo init

```bash
repo init -u https://github.com/PixelOS-AOSP/android_manifest.git \
  -b seventeen --depth=1 --manifest-depth=1 \
  --partial-clone --clone-filter=blob:none \
  --git-lfs --no-clone-bundle --no-tags --platform=linux
```

## Local manifests

```bash
cp local_manifests/*.xml .repo/local_manifests/
```

The three project entries add the device, kernel and vendor repositories.
The compatibility manifest is empty: no upstream HAL projects are removed.
M2381 selects its source stacks through product configuration, so the same
checkout retains these projects for other devices.

## Sync

```bash
repo sync -c -j4 --no-clone-bundle --no-tags
repo manifest -r -o revisions.xml
```

## Device compatibility

Android 17 no longer requires patches to libbase, VNDK33, Lineage's global
kernel-header generator or Soong. The device uses official LineageOS
`libbase_shim` with pinned ELF dependency fixups, a product linker fragment,
and the upstream prebuilt kernel-header interface.

```bash
python3 device/meizu/m2381/tools/configure_blob_compat.py --aosp /path/to/aosp
python3 tools/apply_platform_patches.py --aosp /path/to/aosp --require-unpatched
```

For an older patched checkout, commit existing changes and use `--restore`
with the platform tool. Unknown revisions are refused. See
[platform isolation and official references](docs/platform-isolation.md).
The recorded patch series remains only for migration and historical review.

## Build

```bash
scripts/build-pixelos.sh /path/to/aosp [JOBS]
```

The script checks local inputs, LFS payloads, pinned blob compatibility and
unpatched platform sources, then builds `custom_m2381-<release>-userdebug`.

## Documentation

`docs/` holds build, status, charging, firmware, patches and compatibility
notes. `diagnostics/` keeps frozen reference dumps from earlier bring-up
rounds; nothing there is applied automatically.
