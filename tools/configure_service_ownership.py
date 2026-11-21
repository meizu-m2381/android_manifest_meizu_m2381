#!/usr/bin/env python3
"""Keep one hardware owner for the M2381 Power/BootControl services.

Thermal and NFC retain the stock HAL needed by vendor clients; their source
services are not selected by device.mk. Original extracted files stay intact.
"""
import argparse
from pathlib import Path
from configure_connectivity import configure

SOURCE_OWNED = {
    'vendor/bin/hw/android.hardware.power-service',
    'vendor/etc/init/android.hardware.power-service.rc',
    'vendor/bin/hw/android.hardware.boot@1.2-service',
    'vendor/etc/init/android.hardware.boot@1.2-service.rc',
    'vendor/etc/vintf/manifest/android.hardware.boot@1.2.xml',
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', type=Path)
    configure(parser.parse_args().tree, SOURCE_OWNED)
