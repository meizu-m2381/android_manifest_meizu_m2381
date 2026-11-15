# android_manifest_meizu_m2381

Repository manifests, platform patches and tooling for building the Meizu 20
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

| File | Purpose |
| ---- | ------- |
| `00-m2381-prebuilt-kernel.xml` | Keeps upstream dependencies; no projects excluded |
| `01-m2381-excluded-projects.xml` | Removes `hardware/qcom-caf/sm8550/display` |

The display project is removed because this device installs the matched stock
display stack from vendor blobs and builds no module from that source tree.
`libdisplayconfig.qti` still resolves, through the namespace import in the
remaining `hardware/qcom-caf/sm8550/Android.bp` linkfile, to
`vendor/qcom/opensource/display`.

## Sync

```bash
repo sync -c -j4 --no-clone-bundle --no-tags
repo manifest -r -o revisions.xml
```

## Platform patches

`patches/platform-17-series.json` lists five required patches for Android 17.
Apply or verify them read-only:

```bash
python3 tools/apply_platform_patches.py --aosp /path/to/aosp
python3 tools/apply_platform_patches.py --aosp /path/to/aosp --apply
```

| Patch | Target | Purpose |
| ----- | ------ | ------- |
| 0001 | `system/libbase/strings.cpp` | Non-template `Trim` symbol for API 33 vendor HALs |
| 0002 | `system/libbase/file.cpp` | `WriteStringToFd` and `Basename` symbols for the same |
| 0003 | `prebuilts/vndk/v33/arm/configs/llndk.libraries.txt` | Add `libapexsupport.so` to the LLNDK list |
| 0004 | `prebuilts/vndk/v33/arm64/configs/llndk.libraries.txt` | Same for arm64 |
| 0005 | `vendor/lineage/build/soong/Android.bp` | Build-only kernel header for the prebuilt kernel |

Each entry records the SHA-256 of the file before and after patching. Unknown
source revisions are rejected rather than force-applied.

## Build

```bash
scripts/build-pixelos.sh /path/to/aosp [JOBS]
```

The script checks local inputs and LFS payloads, requires the platform patches
to be applied, then builds `custom_m2381-<release>-userdebug`.

## Documentation

`docs/` holds build, status, charging, firmware, patches and compatibility
notes. `diagnostics/` keeps frozen reference dumps from earlier bring-up
rounds; nothing there is applied automatically.
