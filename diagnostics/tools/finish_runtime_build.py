"""Finish the in-flight build, then rebuild to include late ABI fixes.

Stream concise build progress; never run two Ninja builds against the same out.
"""

import argparse
import os
import re
import subprocess
import time
from pathlib import Path


def follow(log, alive):
    offset, last = 0, -1
    while True:
        if log.exists():
            with log.open(errors="replace") as source:
                source.seek(offset)
                lines = source.readlines()
                offset = source.tell()
            for line in lines:
                match = re.match(r"\[\s*(\d+)%\s+\d+/(\d+)(?:\s|\])", line)
                if match and int(match[2]) > 1000 and int(match[1]) >= last + 5:
                    last = int(match[1])
                    print(line.strip()[:220], flush=True)
                if "FAILED:" in line or re.search(r"(?:^|\s)error:", line) or "failed to build" in line:
                    print(line.strip()[:1000], flush=True)
        if not alive():
            return
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aosp", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--build-pid", type=int, required=True)
    parser.add_argument("--targets", nargs="+", default=["vendorimage"])
    args = parser.parse_args()
    initial = Path(f"/proc/{args.build_pid}/cmdline")
    if initial.exists():
        assert b"soong_ui" in initial.read_bytes(), "Unexpected build PID"
        print("Waiting for existing build to finish", flush=True)
        follow(args.audit / "build-runtime.log", initial.exists)
    print("Incremental rebuild including all ABI fixes", flush=True)
    assert all(re.fullmatch(r"[a-z_]+", target) for target in args.targets)
    command = ("set -e; source build/envsetup.sh >/dev/null; "
               "lunch custom_m2381-bp4a-userdebug; "
               "m " + " ".join(args.targets) + " -j12")
    log = args.audit / "build-runtime-final.log"
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin:" + env.get("PATH", "")
    with log.open("w") as output:
        process = subprocess.Popen(["bash", "-c", command], cwd=args.aosp,
                                   stdout=output, stderr=subprocess.STDOUT, env=env)
        follow(log, lambda: process.poll() is None)
        result = process.wait()
    print("Final image build exit:", result, flush=True)
    if result:
        print("\n".join(line[:250] for line in log.read_text(errors="replace").splitlines()[-25:]), flush=True)
    raise SystemExit(result)


if __name__ == "__main__":
    main()
