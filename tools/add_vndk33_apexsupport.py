"""Retired platform mutation entry point; retained to explain migration."""

if __name__ == "__main__":
    raise SystemExit(
        "This platform patch tool is retired. Use the device PRODUCT_VENDOR_LINKER_CONFIG_FRAGMENTS requirement; the VNDK33 snapshot libbinder does not need libapexsupport. "
        "See docs/platform-isolation.md; use apply_platform_patches.py --restore for old checkouts."
    )
