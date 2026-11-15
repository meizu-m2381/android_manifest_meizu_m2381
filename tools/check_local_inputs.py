#!/usr/bin/env python3
"""Validate the exact build input set without executing any vendor code."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(root, entries):
    errors = []
    for entry in entries:
        path = root / entry["path"]
        if not path.is_file():
            errors.append((entry["path"], "missing"))
        elif path.stat().st_size < 1024 and path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            errors.append((entry["path"], "Git LFS pointer: run git lfs pull"))
        elif path.stat().st_size != entry["size"] or digest(path) != entry["sha256"]:
            errors.append((entry["path"], "hash mismatch"))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    entries = json.loads((ROOT / "provenance/local-inputs.json").read_text())["files"]
    errors = check(args.root, entries)
    for path, reason in errors[:30]:
        print(reason, path)
    print(f"Local inputs: {len(entries)} checked, {len(errors)} errors")
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
