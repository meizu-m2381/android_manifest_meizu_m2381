"""Check retired service packaging without removing active vendor dependencies."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configure_connectivity import configure
from configure_service_ownership import SOURCE_OWNED


class ServiceOwnershipTest(unittest.TestCase):
    def test_single_owner_retains_thermal_nfc_and_boot_interface_libraries(self):
        retained = ['vendor/bin/hw/android.hardware.thermal@2.0-service.qti-v2',
                    'vendor/bin/hw/vendor.nxp.hardware.nfc@2.0-service',
                    'vendor/lib64/android.hardware.boot@1.2.so',
                    'vendor/lib64/android.hardware.thermal@2.0.so']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vendor = root / 'vendor/meizu/m2381'
            device = root / 'device/meizu/m2381'
            vendor.mkdir(parents=True)
            device.mkdir(parents=True)
            paths = sorted(SOURCE_OWNED) + retained
            make = []
            for index, path in enumerate(paths):
                original = vendor / 'proprietary' / path
                original.parent.mkdir(parents=True, exist_ok=True)
                original.write_bytes(b'preserved original')
                make.append('include $(CLEAR_VARS)\n'
                            f'LOCAL_MODULE := stock_{index}\n'
                            f'LOCAL_SRC_FILES := proprietary/{path}\n'
                            'include $(BUILD_PREBUILT)\n\n')
            (vendor / 'Android.mk').write_text(''.join(make))
            (vendor / 'm2381-vendor.mk').write_text('PRODUCT_PACKAGES += \\\n' +
                    ''.join(f'    stock_{i} \\\n' for i in range(len(paths))) + '\n')
            (device / 'proprietary-files.txt').write_text('\n'.join(paths) + '\n')
            configure(root, SOURCE_OWNED)
            installed = (vendor / 'Android.mk').read_text()
            for path in SOURCE_OWNED:
                self.assertNotIn(f'proprietary/{path}\n', installed)
            for path in retained:
                self.assertIn(f'proprietary/{path}\n', installed)
            for path in paths:
                self.assertEqual((vendor / 'proprietary' / path).read_bytes(),
                                 b'preserved original')
            outputs = [vendor/'Android.mk', vendor/'m2381-vendor.mk',
                       device/'proprietary-files.txt']
            first = [p.read_bytes() for p in outputs]
            configure(root, SOURCE_OWNED)
            self.assertEqual(first, [p.read_bytes() for p in outputs])


if __name__ == '__main__':
    unittest.main()
