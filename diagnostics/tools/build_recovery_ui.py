"""Build a visible Flyme recovery image that keeps the root ADB diagnostic hook.

Run this script inside WSL with the AOSP tree available. It only creates an image;
flashing remains a separate fastboot step.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command):
    return subprocess.run([str(x) for x in command], check=True,
                          capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aosp', type=Path, required=True)
    parser.add_argument('--source-image', type=Path, required=True,
                        help='Existing ADB diagnostic recovery image')
    parser.add_argument('--output-image', type=Path, required=True)
    args = parser.parse_args()
    if args.source_image.stat().st_size != 100 * 1024 * 1024:
        raise ValueError('source recovery image must be exactly 100 MiB')
    mkboot = args.aosp / 'system/tools/mkbootimg'
    avb = args.aosp / 'external/avb/avbtool.py'
    lz4 = args.aosp / 'out/host/linux-x86/bin/lz4'
    with tempfile.TemporaryDirectory(prefix='m2381-recovery-ui-') as temp:
        work = Path(temp)
        unpack = work / 'unpacked'
        run([args.aosp / 'system/tools/mkbootimg/unpack_bootimg.py',
             '--boot_img', args.source_image, '--out', unpack, '--format', 'mkbootimg'])
        run([lz4, '-d', unpack / 'ramdisk', work / 'base.cpio'])
        prepare = Path(__file__).with_name('prepare_recovery_adb.py')
        run(['python3', prepare, work / 'base.cpio', work / 'ui.cpio', '--show-ui'])
        run([lz4, '-l', '-12', '-f', work / 'ui.cpio', work / 'ramdisk'])
        raw = work / 'recovery-ui-raw.img'
        run([mkboot / 'mkbootimg.py', '--header_version', '4',
             '--os_version', '13.0.0', '--os_patch_level', '2023-10',
             '--kernel', unpack / 'kernel', '--ramdisk', work / 'ramdisk',
             '--output', raw])
        run(['python3', avb, 'add_hash_footer', '--image', raw,
             '--partition_name', 'recovery', '--partition_size', str(100 * 1024 * 1024),
             '--algorithm', 'NONE'])
        args.output_image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raw, args.output_image)
    if args.output_image.stat().st_size != 100 * 1024 * 1024:
        raise ValueError('generated recovery image is not exactly 100 MiB')
    run(['python3', avb, 'info_image', '--image', args.output_image])
    print(f'Created visible recovery image: {args.output_image}')


if __name__ == '__main__':
    main()
