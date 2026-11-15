#!/usr/bin/env python3
"""Check or reconstruct the private round47 helper from a known stock input."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    for entry in json.loads((ROOT / 'provenance/diagnostic-inputs.json').read_text(encoding='utf-8')):
        data = (ROOT / entry['source']).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['before_sha256']:
            raise ValueError('Unknown stock diagnostic input')
        offset = entry['insert_offset']
        result = data[:offset] + entry['insert_utf8'].encode('utf-8') + data[offset:]
        if hashlib.sha256(result).hexdigest() != entry['after_sha256']:
            raise ValueError('Reconstructed helper checksum mismatch')
        target = ROOT / entry['path']
        if target.exists() and target.read_bytes() != result:
            raise ValueError('Existing diagnostic helper differs')
        if args.apply and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.tmp')
            temporary.write_bytes(result)
            temporary.replace(target)
        print('verified private diagnostic reconstruction:', entry['path'])


if __name__ == '__main__':
    main()
