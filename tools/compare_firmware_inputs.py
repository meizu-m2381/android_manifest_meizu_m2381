#!/usr/bin/env python3
"""Compare a vendor dump with the bundled baseline without importing or patching it."""
import argparse
import json
from pathlib import Path
from check_local_inputs import ROOT, digest


def compare(source):
    entries = json.loads((ROOT / 'provenance/local-inputs.json').read_text(encoding='utf-8'))['files']
    results = []
    for entry in entries:
        if entry['kind'] != 'vendor-input':
            continue
        candidates = [source / entry['path'], source / entry['partition_path']]
        path = next((p for p in candidates if p.is_file()), None)
        record = {'path': entry['partition_path'], 'expected_sha256': entry['sha256']}
        if path is None:
            record['status'] = 'missing'
        else:
            actual = digest(path)
            record['actual_sha256'] = actual
            record['status'] = ('matching-final' if actual == entry['sha256'] else
                                'matching-before-fixup' if actual == entry.get('unpatched_workspace_sha256') else
                                'different-version')
        results.append(record)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, help='Write a JSON report; use local/ to keep it out of Git')
    args = parser.parse_args()
    results = compare(args.source.resolve(strict=True))
    counts = {status: sum(x['status'] == status for x in results) for status in
              ['matching-final', 'matching-before-fixup', 'different-version', 'missing']}
    if args.report:
        if args.report.exists():
            parser.error('Report already exists; use a new path')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'counts': counts, 'files': results}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts))
    for record in [x for x in results if x['status'] in {'different-version', 'missing'}][:20]:
        print(record['status'], record['path'])
    print('Comparison only; firmware compatibility has not been validated')
    raise SystemExit(bool(counts['different-version'] or counts['missing']))


if __name__ == '__main__':
    main()
