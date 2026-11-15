"""Remove stock combined policy installation while preserving original inputs."""
import argparse
from pathlib import Path

from configure_connectivity import configure


SOURCE_OWNED = {
    "odm/etc/selinux/precompiled_sepolicy" + suffix
    for suffix in ("", ".plat_sepolicy_and_mapping.sha256",
                   ".product_sepolicy_and_mapping.sha256",
                   ".system_ext_sepolicy_and_mapping.sha256")
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    configure(parser.parse_args().tree, SOURCE_OWNED)
