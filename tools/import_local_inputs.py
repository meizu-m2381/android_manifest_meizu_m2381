#!/usr/bin/env python3
"""Import named inputs from a partition dump or an existing workspace.

Only manifest paths are read and written. Inputs must match known hashes.
For the unpatched vendor set, --aosp provides the matching patchelf tool.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from check_local_inputs import ROOT, check, digest


def apply_text(root, fixups):
    for item in fixups:
        path = root / item["path"]
        current = digest(path)
        if current == item["after_sha256"]:
            continue
        if current != item["before_sha256"]:
            raise ValueError(f"Unknown input for text fixup: {path}")
        text = path.read_text(encoding="utf-8")
        for edit in reversed(item["edits"]):
            start = edit["offset"]
            end = start + len(edit["before"])
            if text[start:end] != edit["before"]:
                raise ValueError(f"Text fixup context mismatch: {path}")
            text = text[:start] + edit["after"] + text[end:]
        # Replace rather than write through possible local hard links.
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
        if digest(path) != item["after_sha256"]:
            raise ValueError(f"Text fixup result mismatch: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Workspace root; for vendor files a partition dump root also works")
    parser.add_argument("--aosp", type=Path,
                        help="Required only when importing unpatched tinyxml2 inputs")
    parser.add_argument("--dry-run", action="store_true", help="Validate sources and conflicts without copying")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    if source == ROOT:
        parser.error("Source and destination must differ")
    entries = json.loads((ROOT / "provenance/local-inputs.json").read_text())["files"]
    plan = []
    for entry in entries:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid manifest path")
        candidates = [source / relative]
        if entry.get("partition_path"):
            candidates.append(source / entry["partition_path"])
        src = next((p for p in candidates if p.is_file()), None)
        if src is None:
            raise FileNotFoundError(f"Missing {relative}; see docs/local-inputs.md")
        actual = digest(src)
        allowed = {entry["sha256"], entry.get("unpatched_workspace_sha256")}
        if actual not in allowed:
            raise ValueError(f"Unknown source hash: {relative}")
        dest = ROOT / relative
        if dest.exists() and digest(dest) not in allowed:
            raise ValueError(f"Refusing to overwrite different local input: {relative}")
        plan.append((src, dest, entry, actual))
    requires_binary_fixups = any(
        actual != entry["sha256"] and src.suffix not in {".rc", ".xml", ".json", ".txt"}
        for src, _, entry, actual in plan
    )
    if args.dry_run:
        print(f"Validated {len(plan)} source inputs; binary fixups required: {requires_binary_fixups}")
        return
    if requires_binary_fixups and args.aosp is None:
        parser.error("Unpatched binary inputs require --aosp")
    # All source hashes and destination conflicts are checked before copying.
    for src, dest, entry, actual in plan:
        if dest.is_file() and digest(dest) == entry["sha256"]:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        temporary = dest.with_name(dest.name + ".tmp")
        shutil.copy2(src, temporary)
        temporary.replace(dest)
    fixups = json.loads((ROOT / "patches/vendor-text-fixups.json").read_text(encoding="utf-8"))
    apply_text(ROOT, fixups)
    if requires_binary_fixups:
        # The fixer accepts an AOSP layout. Expose only this repository's vendor inputs
        # and the external patchelf tool in a local staging directory.
        stage = ROOT / "local/fixup-tree"
        stage.mkdir(parents=True, exist_ok=True)
        for rel, target in [("vendor", ROOT / "vendor"),
                            ("prebuilts", args.aosp.resolve() / "prebuilts")]:
            link = stage / rel
            if not link.exists():
                link.symlink_to(target, target_is_directory=True)
            elif link.resolve() != target.resolve():
                raise ValueError(f"Staging link points elsewhere: {link}")
        backup = ROOT / "local/original-inputs"
        subprocess.run([sys.executable, str(ROOT / "tools/apply_tinyxml2_vendor_fixups.py"),
                        str(stage), str(backup / "tinyxml2")], check=True)
        for driver in ["egl", "vulkan"]:
            subprocess.run([sys.executable, str(ROOT / "tools/fix_egl_mapper_getstub.py"),
                            "--aosp", str(stage), "--backup", str(backup / driver),
                            "--driver", driver], check=True)
    errors = check(ROOT, entries)
    if errors:
        raise ValueError(f"Imported input verification failed: {errors[:10]}")
    print(f"Imported and verified {len(entries)} private inputs; nothing was flashed")


if __name__ == "__main__":
    main()
