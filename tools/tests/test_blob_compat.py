"""Behavior checks for pinned vendor ELF fixup failure safety."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(os.environ.get('M2381_AOSP_ROOT'), 'requires real pinned ARM blobs and patchelf in WSL')
class BlobTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.aosp = Path(os.environ['M2381_AOSP_ROOT'])
        self.device = self.aosp / 'device/meizu/m2381'
        self.compat = load('blob_compat', self.device / 'tools/configure_blob_compat.py')
        self.manifest = json.loads((self.device / 'configs/compat/libbase-fixups.json').read_text())
        self.vendor = self.root / 'vendor'
        for entry in self.manifest['files']:
            target = self.vendor / 'proprietary' / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.aosp / 'vendor/meizu/m2381/proprietary' / entry['path'], target)
        self.vendor.joinpath('Android.mk').write_text(''.join(
            'LOCAL_SRC_FILES := proprietary/' + e['path'] + '\n' for e in self.manifest['files']))

    def test_fixups_are_repeatable_and_leave_originals_unchanged(self):
        self.compat.configure(self.aosp, self.device, self.vendor, True)
        self.compat.configure(self.aosp, self.device, self.vendor, True)
        self.compat.configure(self.aosp, self.device, self.vendor)
        tool = self.aosp / 'prebuilts/extract-tools/linux-x86/bin' / self.manifest['patchelf']
        for entry in self.manifest['files']:
            self.assertEqual(self.compat.sha256(self.vendor / 'proprietary' / entry['path']), entry['sha256'])
            fixed = self.vendor / 'compat' / entry['path']
            dependencies = subprocess.check_output([str(tool), '--print-needed', str(fixed)], text=True).splitlines()
            for needed in entry.get('add_needed', [self.manifest['library']]):
                self.assertEqual(dependencies.count(needed), 1)
            for old, new in entry.get('replace_needed', {}).items():
                self.assertNotIn(old, dependencies)
                self.assertEqual(dependencies.count(new), 1)

    def test_known_previous_fixup_can_upgrade_but_check_rejects_it(self):
        self.compat.configure(self.aosp, self.device, self.vendor, True)
        entry = next(e for e in self.manifest['files'] if e.get('previous_fixed_sha256'))
        output = self.vendor / 'compat' / entry['path']
        # Reconstruct the previous add-needed-only version from the original.
        output.write_bytes((self.vendor / 'proprietary' / entry['path']).read_bytes())
        tool = self.aosp / 'prebuilts/extract-tools/linux-x86/bin' / self.manifest['patchelf']
        subprocess.run([str(tool), '--add-needed', self.manifest['library'], str(output)], check=True)
        self.assertIn(self.compat.sha256(output), entry['previous_fixed_sha256'])
        with self.assertRaises(ValueError):
            self.compat.configure(self.aosp, self.device, self.vendor)
        self.compat.configure(self.aosp, self.device, self.vendor, True)
        self.assertEqual(self.compat.sha256(output), entry['fixed_sha256'])

    def test_media_helper_is_reproducible_and_preserves_upstream(self):
        sys.path.insert(0, str(self.device / 'tools'))
        self.addCleanup(sys.path.remove, str(self.device / 'tools'))
        helper = load('media_helper', self.device / 'tools/prepare_media_helper.py')
        config = json.loads((self.device / 'configs/compat/media-helper.json').read_text())
        source = self.aosp / config['source']
        output = self.root / 'helper.so'
        helper.prepare(self.aosp, output)
        first = output.read_bytes()
        helper.prepare(self.aosp, output)
        self.assertEqual(output.read_bytes(), first)
        self.assertEqual(hashlib.sha256(first).hexdigest(), config['fixed_sha256'])
        self.assertEqual(self.compat.sha256(source), config['sha256'])
        # An unknown upstream revision must fail before changing an existing output.
        isolated = self.root / 'unknown-aosp'
        unknown = isolated / config['source']
        unknown.parent.mkdir(parents=True)
        unknown.write_bytes(b'changed upstream')
        with self.assertRaises(ValueError):
            helper.prepare(isolated, output)
        self.assertEqual(output.read_bytes(), first)

    def test_unknown_last_original_preserves_all_outputs_and_rules(self):
        source = self.vendor / 'proprietary' / self.manifest['files'][-1]['path']
        source.write_bytes(b'unknown blob')
        original_rules = (self.vendor / 'Android.mk').read_bytes()
        with self.assertRaises(ValueError):
            self.compat.configure(self.aosp, self.device, self.vendor, True)
        self.assertFalse((self.vendor / 'compat').exists())
        self.assertEqual((self.vendor / 'Android.mk').read_bytes(), original_rules)

    def test_conflicting_last_output_preserves_other_outputs_and_rules(self):
        output = self.vendor / 'compat' / self.manifest['files'][-1]['path']
        output.parent.mkdir(parents=True)
        output.write_bytes(b'existing user output')
        original_rules = (self.vendor / 'Android.mk').read_bytes()
        with self.assertRaises(ValueError):
            self.compat.configure(self.aosp, self.device, self.vendor, True)
        self.assertFalse((self.vendor / 'compat' / self.manifest['files'][0]['path']).exists())
        self.assertEqual(output.read_bytes(), b'existing user output')
        self.assertEqual((self.vendor / 'Android.mk').read_bytes(), original_rules)

    def test_invalid_binary_fixup_preserves_all_outputs_and_rules(self):
        device = self.root / 'device'
        config = device / 'configs/compat/libbase-fixups.json'
        config.parent.mkdir(parents=True)
        rules = (self.vendor / 'Android.mk').read_bytes()
        for invalid in ['count', 'length']:
            manifest = json.loads(json.dumps(self.manifest))
            entry = next(e for e in manifest['files'] if e.get('binary_replacements'))
            replacement = entry['binary_replacements'][0]
            if invalid == 'count':
                replacement['count'] += 1
            else:
                replacement['after'] += 'x'
            config.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.compat.configure(self.aosp, device, self.vendor, True)
            self.assertFalse((self.vendor / 'compat').exists())
            self.assertEqual((self.vendor / 'Android.mk').read_bytes(), rules)

    def test_invalid_offset_fixup_preserves_all_outputs_and_rules(self):
        device = self.root / 'device'
        config = device / 'configs/compat/libbase-fixups.json'
        config.parent.mkdir(parents=True)
        rules = (self.vendor / 'Android.mk').read_bytes()
        for invalid in ['bytes', 'length', 'negative', 'past_end', 'overlap']:
            manifest = json.loads(json.dumps(self.manifest))
            entry = next(e for e in manifest['files'] if e.get('offset_replacements'))
            replacement = entry['offset_replacements'][0]
            if invalid == 'bytes':
                replacement['before_hex'] = '00000000'
            elif invalid == 'length':
                replacement['after_hex'] += '00'
            elif invalid == 'negative':
                replacement['offset'] = '-1'
            elif invalid == 'past_end':
                replacement['offset'] = '0x10000000'
            else:
                entry['offset_replacements'].append(dict(replacement))
            config.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.compat.configure(self.aosp, device, self.vendor, True)
            self.assertFalse((self.vendor / 'compat').exists())
            self.assertEqual((self.vendor / 'Android.mk').read_bytes(), rules)


if __name__ == '__main__':
    unittest.main()
