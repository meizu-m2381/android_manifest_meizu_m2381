import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'configure_connectivity', Path(__file__).resolve().parents[1] / 'configure_connectivity.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceOwnedUsbTest(unittest.TestCase):
    def test_unselected_provider_cannot_override_source_install_target(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            vendor = tree / 'vendor/meizu/m2381'
            device = tree / 'device/meizu/m2381'
            vendor.mkdir(parents=True)
            device.mkdir(parents=True)
            paths = ['vendor/etc/init/hw/init.qcom.usb.rc',
                     'vendor/bin/init.qcom.usb.sh', 'vendor/etc/usb_compositions.conf']
            rules = []
            for i, path in enumerate(paths + ['vendor/etc/unrelated.conf']):
                raw = vendor / 'proprietary' / path
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_bytes(b'original stock input\n')
                rules.append('include $(CLEAR_VARS)\n'
                             f'LOCAL_MODULE := stock_{i}\n'
                             f'LOCAL_SRC_FILES := proprietary/{path}\n'
                             'include $(BUILD_PREBUILT)\n\n')
            (vendor / 'Android.mk').write_text(''.join(rules))
            # stock_0 is deliberately absent: an unselected Make module still
            # defines a global install rule and used to override the source RC.
            (vendor / 'm2381-vendor.mk').write_text(
                'PRODUCT_PACKAGES += \\\n    init.qcom.usb.rc \\\n    stock_1 \\\n    stock_2 \\\n    stock_3\n')
            manifest = device / 'proprietary-files.txt'
            manifest.write_text('\n'.join(paths + ['vendor/etc/unrelated.conf']) + '\n')
            module.configure(tree)
            generated = (vendor / 'Android.mk').read_text()
            for i in range(3):
                self.assertNotIn(f'LOCAL_MODULE := stock_{i}\n', generated)
            self.assertIn('LOCAL_MODULE := stock_3\n', generated)
            packages = (vendor / 'm2381-vendor.mk').read_text()
            self.assertIn('    init.qcom.usb.rc \\\n', packages)
            self.assertIn('    stock_3\n', packages)
            self.assertEqual(manifest.read_text(), 'vendor/etc/unrelated.conf\n')
            for path in paths:
                self.assertEqual((vendor / 'proprietary' / path).read_bytes(),
                                 b'original stock input\n')
            outputs = [vendor / 'Android.mk', vendor / 'm2381-vendor.mk', manifest]
            before = [path.read_bytes() for path in outputs]
            module.configure(tree)
            self.assertEqual([path.read_bytes() for path in outputs], before)


if __name__ == '__main__':
    unittest.main()
