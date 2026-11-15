#!/usr/bin/env python3
"""Give the source M2381 Health service sole ownership; keep stock inputs."""
import argparse
from pathlib import Path
from configure_connectivity import configure

SOURCE_OWNED = {
    "vendor/bin/hw/android.hardware.health-service.qti",
    "vendor/etc/init/android.hardware.health-service.qti.rc",
    "vendor/etc/vintf/manifest/android.hardware.health-service.qti.xml",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    configure(parser.parse_args().tree, SOURCE_OWNED)
