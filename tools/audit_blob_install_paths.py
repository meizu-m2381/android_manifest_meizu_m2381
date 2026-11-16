#!/usr/bin/env python3
"""Check that prebuilt libraries and modules keep their runtime subdirectories."""
import argparse
from collections import defaultdict
from pathlib import Path, PurePosixPath
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--makefile', type=Path,
                        default=Path('vendor/meizu/m2381/Android.mk'))
    args = parser.parse_args()
    errors = []
    destinations = defaultdict(list)
    checked = 0
    for block in args.makefile.read_text(encoding='utf-8').split('include $(CLEAR_VARS)'):
        source = re.search(r'^LOCAL_SRC_FILES := (?:proprietary|compat)/([^/]+)/(lib(?:64)?/[^\n]+)$', block, re.M)
        if not source:
            continue
        part, relative = source.groups()
        module_path = re.search(r'^LOCAL_MODULE_PATH := (.+)$', block, re.M)
        stem = re.search(r'^LOCAL_MODULE_STEM := (.+)$', block, re.M)
        if not module_path or not stem:
            errors.append('Missing install rule: ' + source[0])
            continue
        expected = '$(TARGET_OUT_' + part.upper() + ')/' + str(PurePosixPath(relative).parent)
        if module_path[1] != expected:
            errors.append(f'{part}/{relative}: {module_path[1]} != {expected}')
        destinations[module_path[1] + '/' + stem[1]].append(part + '/' + relative)
        checked += 1
    for destination, sources in destinations.items():
        if len(sources) > 1:
            errors.append(f'Duplicate destination {destination}: {sources}')
    print(f'Checked {checked} library/module paths; errors: {len(errors)}')
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
