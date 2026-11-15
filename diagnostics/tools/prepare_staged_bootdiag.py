#!/usr/bin/env python3
"""Create a temporary init entry that pauses before zygote and boot actions."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--pause-before-bpf", action="store_true",
                        help="Defer BPF loading as well as graphical boot until resume")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = args.aosp / "out/target/product/m2381/system/etc/init/hw/init.rc"
    original = root.read_text()
    late_start = original.index("\non late-init\n")
    late_end = original.index("\non early-fs\n", late_start)
    block = original[late_start:late_end]
    deferred = ["zygote-start", "early-boot", "boot"]
    if args.pause_before_bpf:
        deferred = ["load-bpf-programs", "bpf-progs-loaded", *deferred]
    for event in deferred:
        anchor = f"    trigger {event}\n"
        assert block.count(anchor) == 1, event
        block = block.replace(anchor, f"    # Staged diagnostic: defer {event}.\n")
    block += "\non bootdiag-paused\n    start bootdiag_prepare_adb\n\n"
    block += "on property:sys.bootdiag.resume=1\n"
    block += "    setprop sys.bootdiag.phase resumed\n"
    for event in deferred:
        block += f"    trigger {event}\n"
    # Trigger only after the original late-init action has queued filesystem work.
    marker = "    trigger firmware_mounts_complete\n"
    assert block.count(marker) == 1
    block = block.replace(marker, marker + "    trigger bootdiag-paused\n")
    staged = original[:late_start] + block + original[late_end:]
    name = f"init.staged-round{args.round}.rc"
    (args.output / name).write_text(staged)

    tools = Path(__file__).resolve().parent
    entry = (tools / "managed_bootdiag.rc").read_text()
    entry = entry.replace("import /system/etc/init/hw/init.rc",
                          "import /metadata/bootdiag/" + name)
    entry = entry.replace("pixelos-round10", f"pixelos-round{args.round}")
    entry = entry.replace("/bootdiag/watch.sh", f"/bootdiag/watch.round{args.round}.sh")
    entry = entry.replace("/bootdiag/kmsg-wrapper.sh", f"/bootdiag/kmsg-wrapper.round{args.round}.sh")
    # KernelLogger rate limiting hid the BPF verifier failure in earlier rounds.
    entry += "\non early-init\n    write /proc/sys/kernel/printk_ratelimit 0\n"
    entry += "    loglevel 7\n    setprop sys.init_log_level 7\n"
    entry += "\nservice bootdiag_prepare_adb /metadata/bootdiag/busybox sh /metadata/bootdiag/prepare-adb.round" + str(args.round) + ".sh\n"
    entry += "    disabled\n    oneshot\n    user root\n    group root log readproc\n"
    entry += "    seclabel u:r:su:s0\n    stdio_to_kmsg\n"
    (args.output / f"init.round{args.round}.rc").write_text(entry)
    for source, target in (
        ("managed_bootdiag_watch.sh", f"watch.round{args.round}.sh"),
        ("managed_bootdiag_kmsg.sh", f"kmsg-wrapper.round{args.round}.sh"),
        ("staged_bootdiag_adb.sh", f"prepare-adb.round{args.round}.sh"),
    ):
        content = (tools / source).read_text().replace("pixelos-round10", f"pixelos-round{args.round}")
        (args.output / target).write_text(content)
    (args.output / "staged-init-changes.json").write_text(json.dumps({
        "source": str(root), "deferred_events": deferred,
        "resume_property": "sys.bootdiag.resume=1", "staged_root_init": name,
    }, indent=2) + "\n")
    print("Staged diagnostic entry prepared:", args.output)


if __name__ == "__main__":
    main()
